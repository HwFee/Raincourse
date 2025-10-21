import os

from rich.console import Console
from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from config import __VERSION__
from utils.schema import WorkStatus
from utils.utils import jsonFileToDate


def logo(console: Console) -> None:
    console.print(f"雨课堂自动答题（刷课）工具 ,version = {__VERSION__}", style="bold green")


def show_menu(console: Console) -> None:
    console.print(Panel(
        title="[green]菜单",
        renderable=
        Group(
            Text("1.查看课程", justify="center", style="bold yellow"),
            Text("2.查看试题", justify="center", style="bold yellow"),
            Text("3.导出试题", justify="center", style="bold yellow"),
            Text("4.自动答题", justify="center", style="bold yellow"),
            Text("5.答案文件", justify="center", style="bold yellow"),
            Text("6.自动刷课", justify="center", style="bold yellow"),
            Text("7.导出数据", justify="center", style="bold yellow"),
            Text("8.退出登录", justify="center", style="bold yellow"),
            Text("9.切换用户", justify="center", style="bold yellow"),
            Text("10.导出excel", justify="center", style="bold yellow"),
            Text("11.自动刷课(浏览图文，视频，讨论，课后作业)", justify="center", style="bold yellow"),
            Text("12.导出课后作业答案", justify="center", style="bold yellow"),
        ),
        style="bold green",
        width=120,
    ))


def show_course(courses: list, console: Console) -> None:
    tb = Table("序号", "课程id", "课程名", "老师名", border_style="blue", width=116)

    for index, course in enumerate(courses):
        _course = course["course"]
        tb.add_row(
            str(index + 1),
            f"[green]{_course['id']}[/green]",
            _course["name"],
            course["teacher"]['name'],
            style="bold yellow"
        )
    console.print(
        Panel(
            title="[blue]课程信息[/blue]",
            renderable=tb,
            style="bold green",
        )
    )


def show_exam_file(exam_file: list, console: Console) -> None:
    tb = Table("序号", "考试id", "考试名称", "是否可以导出", border_style="blue", width=116)
    for index, item in enumerate(exam_file):
        status_text = "Yes" if item['status'] else "No"
        status_color = "green" if item['status'] else "red"
        tb.add_row(
            str(index + 1),
            item['exam_id'],
            item['exam_name'],
            f"[{status_color}]{status_text}[/{status_color}]",
            style="bold"
        )
    console.print(
        Panel(
            title="[blue]试题文件[/blue]",
            renderable=tb,
            style="bold green",
        )
    )


def show_works(works: list, console: Console) -> None:
    tb = Table("id", "作业id", "作业名称", "作业状态", "分数", "题目数量", border_style="blue", width=116)
    for index, work in enumerate(works):
        status = "未知"
        score = "未知"
        count = "未知"
        try:
            status = str(WorkStatus(work['status']))
            score = str(work["score"])
            count = str(work["problem_count"])
        except:
            pass
        tb.add_row(
            str(index + 1),
            f"[green]{work['courseware_id']}[/green]",
            work['title'],
            # 出现异常就显示未知
            status,
            score,
            count,
            style="bold yellow"
        )
    console.print(
        Panel(
            title="[blue]作业信息",
            renderable=tb,
            style="bold green",
        )
    )


def show_login_method(console: Console) -> None:
    console.print(Panel(
        title="[blue]登录方式",
        renderable=
        Group(
            Text("1.会话记录", justify="center", style="bold yellow"),
            Text("2.扫码登录", justify="center", style="bold yellow"),
        ),
        style="bold green",
        width=120,
    ))


def show_user(user_info: list, console: Console) -> None:
    tb = Table("id", "用户姓名", border_style="blue", width=116)
    for index, user in enumerate(user_info):
        tb.add_row(
            str(index + 1),
            user['name'],
            style="bold yellow"
        )
    console.print(
        Panel(
            title="[blue]用户列表[/blue]",
            renderable=tb,
            style="bold green",
        )
    )


def show_all_answer_file(console: Console) -> None:
    answer_files = []
    answer_file_info = []
    # 回到上一级目录
    dir_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(dir_path, "answer")
    # 如果不存在answer文件夹，就创建一个
    if not os.path.exists(path):
        os.mkdir(path)

    for root, dirs, files in os.walk(path):
        answer_files.append(files)
    for item in answer_files[0]:
        _path = os.path.join(path, item)
        answer_file_info.append(jsonFileToDate(_path)["info"])
    tb = Table("id", "作业名", "文件名称", "文件类型", border_style="blue", width=116)
    for work_info in answer_file_info:
        tb.add_row(
            f"[green]{work_info['exam_id']}[/green]",
            work_info["exam_name"],
            work_info["exam_id"] + ".json",
            work_info['exam_type'],
            style="bold yellow"
        )
    console.print(
        Panel(
            title="[blue]作业文件列表[/blue]",
            renderable=tb,
            style="bold green",
        )
    )


def show_ppt(res, console: Console) -> None:
    tb = Table("id", "ppt_id", "ppt名称", "ppt数量", border_style="blue", width=116)
    i = 1
    for item in res:
        tb.add_row(
            f"[yellow]{str(i)}[/yellow]",
            f"[green]{str(item['courseware_id'])}[/green]",
            item['title'],
            str(item['count']),
            style="bold yellow"
        )
        i = i + 1

    console.print(
        Panel(
            title="[blue]课程列表（ppt）[/blue]",
            renderable=tb,
            style="bold green",
        )
    )
