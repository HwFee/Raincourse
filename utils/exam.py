import time
import re
from rich.console import Console
from api.api import RainAPI
from config import DO_WORK_DURATION_SPAN
from utils.utils import is_exist_answer_file, jsonFileToDate
from utils.ai_solver import AISolver


def find_answer(question_id, console: Console, answer) -> dict:
    """从本地文件查找答案"""
    try:
        if 'data' not in answer or 'results' not in answer['data']:
            console.log(f"答案数据格式错误")
            return {}
        for key, value in enumerate(answer['data']['results']):
            if value['problem_id'] == question_id:
                return value
    except Exception as e:
        console.log(f"查找答案出错: {e}")
        return {}
    return {}


def fetch_answer_from_file(console: Console, exam_id) -> dict:
    """从本地文件读取答案"""
    console.log(f"拉取答案文件 {exam_id}.json")
    _answer = {}
    if is_exist_answer_file("answer", f"{exam_id}.json"):
        _answer = jsonFileToDate("answer", f"{exam_id}.json")
        console.log(f"读取答案文件成功 {exam_id}.json")
        return _answer
    else:
        console.log(f"答案文件不存在 {exam_id}.json")
        console.log(f"退出答题")
        return {}


def construct_answer_formation(question: dict, console: Console, other_answer) -> list:
    """构造答案格式（从本地文件）"""
    try:
        console.log(f"匹配答案...")
        timestamp_seconds = time.time()
        timestamp_milliseconds = int(timestamp_seconds * 1000)

        answer = find_answer(question['ProblemID'], console, other_answer)
        if answer == {}:
            console.log(f"未找到答案 {question['ProblemID']}")
            return []

        question_type = question['TypeText']
        result = []

        if question_type == "单选题":
            result = answer.get('answer', [])
        elif question_type == "多选题":
            result = answer.get('answer', [])
        elif question_type == "填空题":
            _result = answer.get('answer', {})
            result = {}
            for key, value in _result.items():
                result[key] = value[0] if isinstance(value, list) else value
        elif question_type == "判断题":
            result = answer.get('answer', [])
        else:
            console.log(f"还没有实现 {question_type} 类的题型")
            return []

        console.log(f"匹配答案成功 ===> {result}")
        answer_list = [{"problem_id": question['ProblemID'], "result": result, "time": timestamp_milliseconds}]
        return answer_list
    except Exception as e:
        console.log(f"构造答案格式失败: {e}")
        return []


def do_work(console: Console, rain: RainAPI, cache_work, all_question, exam_id) -> None:
    """从本地文件答题（传统方式）"""
    console.log(f"开始答题")
    re_cord = [item['problem_id'] for item in cache_work['data']['results']]
    _answer = fetch_answer_from_file(exam_id=exam_id, console=console)

    if _answer == {}:
        console.log(f"答案数据为空")
        return

    total_questions = all_question['data']['problems'] if all_question['data']['problems'] else []
    console.log(f"获取到 {len(total_questions)} 道题目")

    for index, question in enumerate(total_questions):
        pattern = re.compile(r'<[^>]+>', re.S)
        title = pattern.sub('', question['Body']).replace('\n', '')

        console.log(
            f"拉取题目成功：(id: {question['ProblemID']})[{question['TypeText']}][{title}]({question['Score']} 分)"
        )
        answer = construct_answer_formation(question, console, _answer)

        if not answer:
            console.log(f"跳过题目 {question['ProblemID']}（无答案）")
            continue

        if question['ProblemID'] in re_cord:
            res = rain.post_test(exam_id, re_cord, answer)
        else:
            res = rain.post_test(exam_id, re_cord, answer)
            re_cord.append(question['ProblemID'])

        if res['errcode'] == 0:
            console.log(f"答案保存成功：{res}")
        time.sleep(DO_WORK_DURATION_SPAN)


def ai_do_work(
    console: Console,
    rain: RainAPI,
    cache_work,
    all_question,
    exam_id,
    stop_event=None,
    api_key=None,
    provider_config=None,
) -> None:
    """AI答题 - 只填答案，不提交，并生成答题报告"""
    import json
    import os
    from datetime import datetime

    console.log(f"[bold green]🤖 启动多模型答题系统[/bold green]")

    resolved_api_key = api_key
    if not resolved_api_key:
        raise RuntimeError("未配置模型 API Key，请在设置 -> API配置中填写后再试")

    provider_config = provider_config or {}
    ai_solver = AISolver(
        console=console,
        api_key=resolved_api_key,
        api_type=provider_config.get('api_type', 'minimax_token_plan'),
        base_url=provider_config.get('base_url'),
        model=provider_config.get('default_model'),
    )

    re_cord = [item['problem_id'] for item in cache_work['data']['results']]

    total_questions = all_question['data']['problems'] if all_question['data']['problems'] else []
    console.log(f"[yellow]获取到 {len(total_questions)} 道题目[/yellow]")

    success_count = 0
    fail_count = 0

    # 答题报告数据结构
    report = {
        "exam_id": exam_id,
        "total_questions": len(total_questions),
        "start_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "success_questions": [],
        "failed_questions": [],
        "summary": {}
    }

    # 准备发送答案的请求
    url = f"https://changjiang-exam.yuketang.cn/exam_room/answer_problem"
    headers = {
        "User-Agent": rain.ua,
        "Accept": "application/json, text/plain, */*",
        "Accept-Encoding": "gzip, deflate, zstd",
        "Content-Type": "application/json",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Origin": "https://changjiang-exam.yuketang.cn",
        "Pragma": "no-cache",
        "Referer": f"https://changjiang-exam.yuketang.cn/exam/{exam_id}?isFrom=2",
    }

    for index, question in enumerate(total_questions):
        if stop_event and stop_event.is_set():
            console.log("[yellow]⏹️ 已收到停止请求，答题任务正在结束[/yellow]")
            break

        pattern = re.compile(r'<[^>]+>', re.S)
        title = pattern.sub('', question['Body']).replace('\n', '')

        console.log(
            f"\n[bold magenta]{'='*80}[/bold magenta]"
        )
        console.log(
            f"[bold green]📝 题目 {index+1}/{len(total_questions)}[/bold green]"
        )
        console.log(
            f"[cyan]ID: {question['ProblemID']} | 类型: {question['TypeText']} | 分值: {question['Score']} 分[/cyan]"
        )
        console.log(
            f"[bold magenta]{'='*80}[/bold magenta]"
        )

        # 获取模型答案（带重试）
        ai_answer = ai_solver.solve_question(question, max_retries=3, stop_event=stop_event)

        if not ai_answer:
            console.log(f"[red]❌ AI无法解答此题，跳过[/red]")
            fail_count += 1
            # 记录失败题目
            report["failed_questions"].append({
                "index": index + 1,
                "problem_id": question['ProblemID'],
                "type": question['TypeText'],
                "title": title[:100],
                "score": question['Score'],
                "reason": "AI经过3次重试后仍无法解答"
            })
            continue

        timestamp_milliseconds = int(time.time() * 1000)

        # 直接发送答案
        data = {
            "results": [
                {
                    "problem_id": question['ProblemID'],
                    "result": ai_answer if isinstance(ai_answer, list) else [ai_answer],
                    "time": timestamp_milliseconds
                }
            ],
            "exam_id": exam_id,
            "record": re_cord + [question['ProblemID']]
        }

        console.log(f"[cyan]📤 正在填入答案: {ai_answer}[/cyan]")
        console.log(f"[cyan]   题目ID: {question['ProblemID']}[/cyan]")

        try:
            response = rain.sees.post(url, headers=headers, json=data)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                result = response.json()

                if result.get('errcode') == 0:
                    console.log(f"[green]✅✅✅ 答案填入成功！题目ID: {question['ProblemID']}, 答案: {ai_answer}[/green]")
                    success_count += 1
                    re_cord.append(question['ProblemID'])
                    # 记录成功题目
                    report["success_questions"].append({
                        "index": index + 1,
                        "problem_id": question['ProblemID'],
                        "type": question['TypeText'],
                        "title": title[:100],
                        "score": question['Score'],
                        "answer": ai_answer
                    })
                else:
                    console.log(f"[red]❌❌❌ 填入失败！错误: {result}[/red]")
                    fail_count += 1
                    report["failed_questions"].append({
                        "index": index + 1,
                        "problem_id": question['ProblemID'],
                        "type": question['TypeText'],
                        "title": title[:100],
                        "score": question['Score'],
                        "reason": f"服务器返回错误: {result}"
                    })
            else:
                console.log(f"[red]❌❌❌ HTTP错误: {response.status_code}[/red]")
                fail_count += 1
                report["failed_questions"].append({
                    "index": index + 1,
                    "problem_id": question['ProblemID'],
                    "type": question['TypeText'],
                    "title": title[:100],
                    "score": question['Score'],
                    "reason": f"HTTP错误: {response.status_code}"
                })

        except Exception as e:
            console.log(f"[red]❌❌❌ 请求失败: {e}[/red]")
            fail_count += 1
            report["failed_questions"].append({
                "index": index + 1,
                "problem_id": question['ProblemID'],
                "type": question['TypeText'],
                "title": title[:100],
                "score": question['Score'],
                "reason": f"请求异常: {str(e)}"
            })

        if stop_event and stop_event.is_set():
            console.log("[yellow]⏹️ 已收到停止请求，跳过后续题目[/yellow]")
            break

        console.log(f"[yellow]⏳ 等待 {DO_WORK_DURATION_SPAN} 秒...[/yellow]")
        time.sleep(DO_WORK_DURATION_SPAN)

    # 生成报告摘要
    report["end_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report["summary"] = {
        "success_count": success_count,
        "fail_count": fail_count,
        "success_rate": f"{(success_count/len(total_questions)*100):.2f}%" if total_questions else "0%"
    }

    # 保存答题报告
    report_filename = f"answer_report_{exam_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path = os.path.join("answer", report_filename)

    # 确保answer目录存在
    os.makedirs("answer", exist_ok=True)

    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 打印最终报告
    console.log(f"\n[bold green]🎉 MiniMax答题完成！[/bold green]")
    console.log(f"[green]✅ 成功：{success_count} 道[/green]")
    console.log(f"[red]❌ 失败：{fail_count} 道[/red]")
    console.log(f"[cyan]📊 成功率：{report['summary']['success_rate']}[/cyan]")
    console.log(f"[yellow]⚠️ 请手动检查并提交答案[/yellow]")

    # 如果有失败题目，显示详细信息
    if report["failed_questions"]:
        console.log(f"\n[bold red]📋 无法解答的题目列表：[/bold red]")
        for failed in report["failed_questions"]:
            console.log(f"[red]  - 题目{failed['index']}: ID={failed['problem_id']}, 类型={failed['type']}, 原因={failed['reason']}[/red]")

    console.log(f"\n[bold blue]📄 答题报告已保存至：{report_path}[/bold blue]")
