import datetime
import json
import re
import time
import random

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.padding import Padding
from rich.align import Align
from rich.box import MINIMAL, ROUNDED
from bs4 import BeautifulSoup
from api.api import RainAPI
from config import DEEPSEEK_API_TOKEN, VIDEO_COMPLETION_THRESHOLD, LEARNING_RATE, HEARTBEAT_BATCH_SIZE, \
    RETRY_SLEEP_INTERVAL, LOOP_SLEEP_INTERVAL
from utils.deepseek import DeepSeekClient
from utils.utils import dateToJsonFile, is_exist_answer_file, jsonFileToDate

# 定义任务类型映射
LEAF_TYPE_MAP = {
    3: "公告",
    4: "讨论",
    6: "测验/练习",
}


def format_timestamp(ms_timestamp: int) -> str:
    """将毫秒时间戳转换为可读的日期时间字符串。"""
    if ms_timestamp == 0:
        return "无限制"
    dt_object = datetime.datetime.fromtimestamp(ms_timestamp / 1000)
    return dt_object.strftime("%Y-%m-%d %H:%M:%S")


def process_leaf_info(leaf_data: dict, task_index: int, chapter_id: int, section_id: int | None) -> dict:
    """提取并格式化单个任务（leaf）的信息。"""
    leaf_type = leaf_data.get('leaf_type')
    leaf_type_str = LEAF_TYPE_MAP.get(leaf_type, f"未知 ({leaf_type})")
    return {
        "index": task_index,
        "name": leaf_data.get('name', '未知任务'),
        "id": leaf_data.get('id'),
        "leafinfo_id": leaf_data.get('leafinfo_id'),
        "chapter_id": chapter_id,
        "section_id": section_id,
        "leaf_type": leaf_type,
        "leaf_type_str": leaf_type_str,
        "is_score": "是" if leaf_data.get('is_score') else "否",
        "is_locked": "是" if leaf_data.get('is_locked') else "否",
        "start_time": format_timestamp(leaf_data.get('start_time', 0)),
        "end_time": format_timestamp(leaf_data.get('end_time', 0)),
        "score_deadline": format_timestamp(leaf_data.get('score_deadline', 0)),
        "raw_data": leaf_data
    }


class TaskState:
    """用于存储和管理单个任务状态的类。"""

    # 状态与样式的映射： (状态文本样式, 整行样式)
    STATUS_STYLES = {
        "待处理": ("[yellow]待处理[/yellow]", "default"),
        "处理中...": ("[blue]处理中...[/blue]", "bright_blue"),
        "已完成": ("[green]已完成[/green]", "strike dim"),
        "失败": ("[bold red]失败[/bold red]", "bold red on #300000"),
        "已跳过": ("[grey50]已跳过[/grey50]", "dim"),
    }

    def __init__(self, task_info: dict):
        self.task_info = task_info
        self.status_key = "待处理"
        self.output_log = Text(no_wrap=True)
        self.start_time: datetime.datetime | None = None
        self.end_time: datetime.datetime | None = None

    @property
    def status(self) -> str:
        return self.STATUS_STYLES[self.status_key][0]

    def update_status(self, status_key: str, message: str = ""):
        """更新任务状态，并可选地添加一条消息到日志。"""
        self.status_key = status_key
        if message:
            log_line = Text()
            log_line.append(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] ", style="dim")
            log_line.append(Text.from_markup(message + "\n"))
            self.output_log.append(log_line)

    def get_status_row(self) -> tuple[list[Text | str], str]:
        """为右侧状态表格生成一行数据及该行的样式。"""
        status_text, row_style = self.STATUS_STYLES[self.status_key]

        name_text = Text(self.task_info['name'])

        return [
            str(self.task_info['index']),
            name_text,
            self.task_info['leaf_type_str'],
            Text("是", style="bold yellow") if self.task_info['is_score'] == "是" else Text("否", style="grey50"),
            Text.from_markup(status_text, justify="center")
        ], row_style


def _create_heartbeat_payload(
        rain: RainAPI,
        course_id: str,
        video_id: str,
        classroom_id: str,
        sku_id: str,
        current_frame: int,
        learning_rate: int,
        batch_size: int,
        user_id
) -> list[dict]:
    """构建用于发送的心跳数据包。"""
    timestamp_ms = int(time.time() * 1000)
    heart_data = []

    for i in range(batch_size):
        # 模拟视频播放进度的增加
        current_frame += learning_rate

        heart_data.append({
            "i": 5,
            "et": "loadeddata",
            "p": "web",
            "n": "ali-cdn.xuetangx.com",
            "lob": "cloud4",
            "cp": current_frame,
            "fp": 0,
            "tp": 0,
            "sp": 2,
            "ts": str(timestamp_ms),
            "u": int(user_id),
            "uip": "",
            "c": course_id,
            "v": int(video_id),
            "skuid": sku_id,
            "classroomid": classroom_id,
            "cc": video_id,
            "d": 4976.5,
            "pg": f"{video_id}_{''.join(random.sample('zyxwvutsrqponmlkjihgfedcba1234567890', 4))}",
            "sq": i + 1,  # sq 通常从1开始
            "t": "video",
        })
    return heart_data



def get_answer(problem_id, answer):
    for i in answer:
        if problem_id == i['problem_id']:
            return i['user']['answer']
    return None


def _handle_quiz(task_state: TaskState, rain: RainAPI, course_id, is_export_answer):
    """
    处理测验任务的函数，根据参数决定是回答测验还是导出答案
    参数:
        task_state: TaskState对象，用于跟踪任务状态
        rain: RainAPI对象，用于与API交互
        course_id: 课程ID
        is_export_answer: 布尔值，True表示导出答案，False表示回答测验
    """
    # 获取课程签名
    course_sign = rain.get_course_sign(course_id)['data']['course_sign']
    # 获取任务ID
    leaf_id = task_state.task_info.get('id')
    # 获取任务详细信息
    leaf_info = rain.get_leaf_info(leaf_id, course_id, course_sign)
    # 获取任务类型ID
    leaf_type_id = leaf_info['data']['content_info']['leaf_type_id']
    # 获取SKU ID
    sku_id = leaf_info['data']['sku_id']

    # 如果不是导出答案模式
    if not is_export_answer:
        # 更新任务状态为处理中
        task_state.update_status("处理中...", "开始尝试测验...")
        # 获取作业名称
        work_name = task_state.task_info.get('name', f'未知作业')

        # 尝试加载答案文件
        task_state.update_status("处理中...", f"尝试寻找{leaf_id}.json 答案文件")
        # 检查答案文件是否存在
        if not is_exist_answer_file("answer", f"{leaf_id}.json"):
            task_state.update_status("跳过", f"没有发现{leaf_id}.json 答案文件")
        # 从文件加载答案数据
        answer = jsonFileToDate("answer", f"{leaf_id}.json")
        task_state.update_status("处理中...", f"成功加载{leaf_id}.json 答案文件")
        # 获取练习题列表
        ret = rain.get_exercise_list(course_id, leaf_type_id, sku_id)
        # 遍历所有题目
        for i in ret['data']['problems']:
            time.sleep(random.randint(2, 4))
            try:

                # 获取题目答案
                _answer = get_answer(i['problem_id'],answer['answer']['data']['problems'])
                # 更新任务状态
                task_state.update_status("处理中...", f"{_answer}")
                # 提交答案
                ret = rain.post_work_answer(leaf_id,course_id,course_sign,_answer,i['problem_id'])
                # 检查是否已回答
                if ret['data'] == {}:
                    task_state.update_status("处理中", f"{i['problem_id']} 已经回答了")
                    continue
                # 检查答案是否正确
                if ret['data']['is_correct']:
                    task_state.update_status("处理中", f"{i['problem_id']} 回答正确")
                else:
                    task_state.update_status("处理中", f"{i['problem_id']} 回答错误")
            except Exception as e:
                task_state.update_status("处理中", f"出现了异常的错误:{e}")

        # 更新任务状态为已完成
        task_state.update_status("已完成", f"{ret}")
    else:  # 导出答案模式
        # 获取作业名称
        work_name = task_state.task_info.get('name', f'未知作业')
        # 获取任务ID
        leaf_id = task_state.task_info.get('id')

        # 获取任务详细信息
        leaf_info = rain.get_leaf_info(leaf_id, course_id, course_sign)

        # 获取任务类型ID
        leaf_type_id = leaf_info['data']['content_info']['leaf_type_id']

        # 获取练习题列表
        ret = rain.get_exercise_list(course_id, leaf_type_id, sku_id)

        # 将答案保存为JSON文件
        dateToJsonFile(ret, {"work_id": leaf_id, "course_id": course_id, "work_name": work_name}, "answer",
                       f"{leaf_id}")
        # 更新任务状态
        task_state.update_status("已完成", f"保存答案成功：/answer/{leaf_id}.json")


def _handle_discussion(task_state: TaskState, rain: RainAPI, course_id, is_export_answer):
    if not is_export_answer:
        task_state.update_status("处理中...", "开始参与讨论...")
        # 从 task_state 中获取处理当前任务所需的ID
        leaf_id = task_state.task_info.get('id')
        course_sign = rain.get_course_sign(course_id)['data']['course_sign']
        task_state.update_status("处理中...", f"{course_sign}")
        task_state.update_status("处理中...", f"获取到讨论ID: [cyan]{leaf_id}[/cyan]，正在调用API...")

        leaf_info = rain.get_leaf_info(leaf_id, course_id, course_sign)

        status = rain.get_status(leaf_id, course_id)

        user_id = leaf_info['data']['user_id']
        is_discuss = status['data']
        task_state.update_status("已完成", f"{is_discuss}")
        if is_discuss:
            task_state.update_status("已完成", "跳过。")
            return
        client = DeepSeekClient(deepseek_api_key=DEEPSEEK_API_TOKEN)

        task_state.update_status("处理中...", f"获取 id")

        sku_id = leaf_info['data']['sku_id']
        leaf_type = leaf_info['data']['leaf_type']
        discussion_info = rain.get_discussion_info(leaf_id, course_id, sku_id, leaf_type)
        topic_id = discussion_info['data']['id']

        task_state.update_status("处理中...", f"id 获取成功 {topic_id}")

        question = leaf_info['data']['content_info']['context']
        soup = BeautifulSoup(question, "html.parser")
        question = soup.get_text()
        task_state.update_status("处理中...", f"问题：{question}")
        answer = client.get_answer_by_deepseek(question)
        task_state.update_status("处理中...", f"答案：{answer}")

        ret = rain.post_comment(course_id, user_id, topic_id, answer, course_sign, leaf_id)
        task_state.update_status("已完成", f"{ret['data']['message']}")
    else:
        task_state.update_status("已跳过", f"该类型没有可导出的答案")


def _handle_announcement(task_state: TaskState, rain: RainAPI, course_id, is_export_answer):
    if not is_export_answer:
        task_state.update_status("处理中...", "开始浏览公告...")

        # 从 task_state 中获取处理当前任务所需的ID
        leaf_id = task_state.task_info.get('id')
        course_sign = rain.get_course_sign(course_id)
        task_state.update_status("处理中...", f"获取到公告ID: [cyan]{leaf_id}[/cyan]，正在调用API...")
        status = rain.get_status(leaf_id, course_id)
        is_view = status['data']
        if is_view:
            task_state.update_status("已完成", "跳过。")
            return
        leaf_info = rain.get_leaf_info(leaf_id, course_id, course_sign)

        sku_id = leaf_info['data']['sku_id']
        # 使用 rain 对象和获取到的ID来执行操作
        try:
            ret = rain.read_announcement(leaf_id, course_id, sku_id)
            task_state.update_status("已完成", f"{ret}-公告已成功浏览。")
        except Exception as e:
            task_state.update_status("失败", f"处理公告时出错: {e}")
    else:
        task_state.update_status("已跳过", f"该类型没有可导出的答案")


def _handle_default(task_state: TaskState, rain: RainAPI, course_id, is_export_answer):
    task_state.update_status("处理中...", "处理未知类型任务...")
    task_state.update_status("已跳过", f"任务类型 [bold]{task_state.task_info['leaf_type']}[/bold] 未知，已跳过。")


def get_task_handler(leaf_type: int):
    """根据任务类型返回对应的处理函数。"""
    handlers = { 3: _handle_announcement, 4: _handle_discussion, 6: _handle_quiz}
    return handlers.get(leaf_type, _handle_default)


# --- UI 布局和显示类 ---
class TaskUI:
    """封装所有与Rich UI相关的布局和更新逻辑。"""

    def __init__(self, all_tasks: list[TaskState]):
        self.all_tasks = all_tasks
        self.layout = self._make_layout()

    def _make_layout(self) -> Layout:
        """定义UI的整体布局。"""
        layout = Layout(name="root")
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
        )
        layout["main"].split_row(
            Layout(name="left_column", size=55),
            Layout(name="right_column", ratio=1)
        )
        layout["left_column"].split(
            Layout(name="current_task", ratio=1, minimum_size=15),  # current_task 占据1份比例
            Layout(name="log", ratio=4, minimum_size=10)  # log 占据2份比例，是 current_task 的两倍高
        )
        return layout

    def _update_header(self, current_index: int, total: int) -> Panel:
        grid = Table.grid(expand=True)
        grid.add_column(justify="left", ratio=1)
        grid.add_column(justify="center", ratio=2)
        grid.add_column(justify="right", ratio=1)
        grid.add_row(
            f" [b]任务总数:[/] {total}",
            "[b green]课程任务自动化处理程序[/]",
            f"[b]进度:[/] {current_index}/{total} "
        )
        return Panel(grid, border_style="green", box=ROUNDED)

    def _update_right_pane(self) -> Panel:
        """生成右侧所有任务状态的表格面板。"""
        table = Table(
            title="所有任务状态",
            header_style="bold cyan",
            show_lines=False,
            expand=True,
            box=MINIMAL
        )
        table.add_column("#", width=4, style="dim", justify="right")
        table.add_column("任务名称", min_width=20, ratio=2, no_wrap=True)
        table.add_column("类型", width=10)
        table.add_column("计分", width=5, justify="center")
        table.add_column("状态", width=12, justify="center")

        for task_state in self.all_tasks:
            row_data, row_style = task_state.get_status_row()
            table.add_row(*row_data, style=row_style)

        return Panel(
            Padding(table, (0, 1)),
            title="[bold blue]任务列表[/]",
            border_style="blue",
            box=ROUNDED
        )

    def _update_left_pane(self, task: TaskState) -> Panel:
        """生成左侧当前处理任务的详情面板。"""
        details_table = Table(box=None, show_header=False, expand=True)
        details_table.add_column(width=14, style="bold dim")
        details_table.add_column(ratio=1)

        details_table.add_row("任务名称:", Text(task.task_info['name'], style="bold yellow"))
        details_table.add_row("类型:", task.task_info['leaf_type_str'])
        details_table.add_row("ID:", str(task.task_info['id']))
        details_table.add_row("LeafInfo ID:", str(task.task_info['leafinfo_id']))
        details_table.add_row("是否计分:", task.task_info['is_score'])
        details_table.add_row("是否锁定:", task.task_info['is_locked'])
        details_table.add_row("-" * 20, "")
        details_table.add_row("开放时间:", task.task_info['start_time'])
        details_table.add_row("截止时间:", task.task_info['score_deadline'])
        details_table.add_row("-" * 20, "")
        if task.start_time and task.end_time:
            duration = (task.end_time - task.start_time).total_seconds()
            details_table.add_row("处理耗时:", f"{duration:.2f} 秒")

        return Panel(
            Padding(details_table, (1, 1)),
            title=f"[bold yellow]当前任务: #{task.task_info['index']}[/]",
            border_style="yellow",
            box=ROUNDED
        )

    def _update_footer(self, task: TaskState) -> Panel:
        """生成底部任务输出日志面板。"""
        border_style = "yellow"
        if task.status_key == "已完成":
            border_style = "green"
        elif task.status_key == "失败":
            border_style = "red"

        return Panel(
            task.output_log,
            title=f"[bold {border_style}]任务 #{task.task_info['index']} 输出日志[/]",
            border_style=border_style,
            box=ROUNDED
        )

    def update(self, current_task: TaskState, current_index: int, total: int):
        """一次性更新UI的所有部分。"""
        self.layout["header"].update(self._update_header(current_index, total))
        self.layout["right_column"].update(self._update_right_pane())
        self.layout["current_task"].update(self._update_left_pane(current_task))
        self.layout["log"].update(self._update_footer(current_task))


# --- 主控制函数 ---
def display_course_chapters_dynamic(res: dict, console: Console, rain: RainAPI, course_id, is_export_answer) -> None:
    if not res or 'course_chapter' not in res:
        console.print(Panel(Text("未找到课程章节信息。", style="bold red"), title="错误", border_style="red"))
        return

    # 1. 预处理所有任务，初始化TaskState对象
    all_tasks: list[TaskState] = []
    task_counter = 0
    for chapter_data in res['course_chapter']:
        for item in chapter_data.get('section_leaf_list', []):
            if 'leaf_list' in item:
                for leaf_data in item.get('leaf_list', []):
                    task_counter += 1
                    task_info = process_leaf_info(leaf_data, task_counter, chapter_data.get('id'), item.get('id'))
                    all_tasks.append(TaskState(task_info))
            else:
                task_counter += 1
                task_info = process_leaf_info(item, task_counter, chapter_data.get('id'), None)
                all_tasks.append(TaskState(task_info))

    if not all_tasks:
        console.print(Panel(Text("课程中未发现任何任务点。", style="bold yellow"), title="提示", border_style="yellow"))
        return

    # 2. 初始化UI管理器
    ui = TaskUI(all_tasks)
    total_tasks = len(all_tasks)

    # 3. 使用Live上下文管理器进行动态更新
    # 修改 screen=True 为 screen=False 以便在程序结束后可以使用终端滚动条
    with Live(ui.layout, screen=False, refresh_per_second=12, console=console) as live:
        for i, current_task_state in enumerate(all_tasks):
            # 清空旧日志，准备处理
            current_task_state.output_log = Text(no_wrap=True)

            # 首次更新UI，显示“待处理”状态
            ui.update(current_task_state, i + 1, total_tasks)
            time.sleep(0.5)

            # 获取任务处理函数
            handler = get_task_handler(current_task_state.task_info['leaf_type'])

            current_task_state.start_time = datetime.datetime.now()
            # 执行处理函数，并传入 rain 对象
            try:
                handler(current_task_state, rain, course_id, is_export_answer)
            except Exception as e:
                console.print(f"出现了异常的错误: {e}")
            current_task_state.end_time = datetime.datetime.now()

            # 任务处理完成后，再次更新UI以显示最终结果
            ui.update(current_task_state, i + 1, total_tasks)
            live.refresh()

            # 在处理下一个任务前暂停片刻
            if i < total_tasks - 1:
                time.sleep(1.5)

    console.print(Panel(
        Align.center(Text("所有课程任务处理完毕。", style="bold green")),
        title="[bold green]处理完成[/]",
        border_style="green",
        box=ROUNDED
    ))


# 示例用法:
def show_task_handle(console: Console, all_chapter_data: dict, rain: RainAPI, course_id, is_export_answer):
    """主入口函数，负责调用UI显示和任务处理逻辑。"""
    try:
        # 将 rain 对象传入
        display_course_chapters_dynamic(all_chapter_data, console, rain, course_id, is_export_answer)
    except Exception as e:
        console.print_exception(show_locals=True)
