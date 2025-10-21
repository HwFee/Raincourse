import os
import time
from rich.console import Console

from api.api import RainAPI
from config import PPT_DURATION_SPAN
from utils.exam import do_work
from utils.export_data_excel import export_excel
from utils.seesion_io import SessionManager
from utils.task_handle import show_task_handle
from utils.ui import show_menu, show_course, show_works, show_all_answer_file, show_ppt, show_user, show_exam_file

from utils.utils import dateToJsonFile, jsonFileToDate, is_exist_answer_file, get_files_in_directory, get_exam_files


def select_menu(console: Console, rain: RainAPI) -> None:
    while True:
        show_menu(console)
        choose = console.input("请选择你要选择的功能: ")
        # 查看课程
        if choose == "1":
            res = rain.get_course_list()
            show_course(res['data']['list'], console)
        # 查看作业
        elif choose == "2":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_work(course_id)['data']['activities']
            show_works(res, console)
        elif choose == "3":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)

            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_work(course_id)['data']['activities']
            #
            exam_cover_list = [rain.get_exam_cover(course_id, course['courseware_id']) for course in res]
            print(exam_cover_list)
            show_works(res, console, exam_cover_list)
            index = console.input("请输入你要选择的作业: ")
            work_id = res[int(index) - 1]['courseware_id']

            work_name = res[int(index) - 1]['title']
            res = rain.get_token_work(course_id, work_id)

            # 根据获取的token进入考试
            rain.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')

            res = rain.get_all_answer(work_id)
            if res is None:
                console.log("获取题目失败,请检查是否可以查看试卷")
                continue
            dateToJsonFile(res, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试试题"}, "answer",
                           f"{work_id}")
            console.log(f"保存答案成功：/answer/{work_id}.json")
        elif choose == "4":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_work(course_id)['data']['activities']
            show_works(res, console)
            index = console.input("请输入你要选择的作业: ")
            work_id = res[int(index) - 1]['courseware_id']

            # 获取考试的token
            res = rain.get_token_work(course_id, work_id)

            # 根据获取的token进入考试
            rain.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')

            console.log("获取已完成的问题")
            cache_work = rain.get_cache_work(work_id)

            console.log("获取全部的试题")
            all_question = rain.get_all_question(work_id)
            try:
                do_work(console, rain, cache_work, all_question, work_id)
            except KeyError as e:
                console.log(f"获取题目失败,请检查是否已经提交，如果还未·开始答题，请在手机端先点击开始答题 :{e}")
                continue
        elif choose == "5":
            show_all_answer_file(console)
        elif choose == "6":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_ppt(course_id)
            show_ppt(res['data']['activities'], console)
            console.log(f"获取用户信息", style="bold green")
            user_info = rain.get_user_info()
            console.log(user_info)

            for index, ppt in enumerate(res['data']['activities']):
                if not is_exist_answer_file(ppt['courseware_id'] + ".json"):
                    flag = console.input(
                        f"[red]答案文件不存在 {ppt['title']},是否从当前账号获取答案并保存到文件中 {ppt['title']},确定请输入任意键，退出请输入q: [red]")
                    if flag == "q":
                        return
                    ppt_questions = rain.get_ppt_questions_answer(course_id, ppt['courseware_id'])
                    dateToJsonFile(ppt_questions, {"exam_id": ppt['courseware_id'], "exam_name": ppt['title'],
                                                   "exam_type": "课件试题"}, "answer", f"{ppt['courseware_id']}.json")
                    console.log(f"保存答案成功：/answer/ppt{['courseware_id']}.json")
                    continue
                console.log(f"答案文件存在 {ppt['title']}", style="bold green")
                ppt_questions_answer = jsonFileToDate("answer", f"{ppt['courseware_id']}.json")

                for question in ppt_questions_answer['answer']['data']['problem_results']:
                    # 这里只做了选择和填空的适配
                    console.log(f"开始做题。。", style="bold green")
                    result = question['answer']
                    # 选择题
                    if ";" in question['answer']:
                        # 将字符串分割成单独的信号
                        item = question['answer'].split(";")
                        # 为每个信号分配一个唯一的编号
                        result = {index + 1: signal for index, signal in enumerate(item)}
                    # 填空题

                    res = rain.post_ppt_answer(course_id, question['id'], result)
                    if res['errcode'] != 0:
                        console.log(f"提交答案失败: {res['errmsg']}（这里只做了选择题，填空题没做😶‍🌫️）", style="bold red")
                        continue
                    console.log(
                        f"提交答案成功: Answer:{res['data']['answer']} Result:{res['data']['correct']}, Score:{res['data']['score']}",
                        style="bold green")

                console.log(f"开始浏览ppt: {ppt['title']}", style="bold green")
                rain.view_ppt(ppt['courseware_id'], user_info['data'][0]["user_id"], ppt['count'])
                time.sleep(PPT_DURATION_SPAN)
        # 导出答案
        elif choose == "7":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)

            index = console.input("请选择你要导出数据的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']
            res_works = rain.get_work(course_id)['data']['activities']
            for index, work in enumerate(res_works):
                if work['type'] == 20:
                    work_extra_info = rain.get_pub_new_prob(course_id, work['courseware_id'])
                    work.update(work_extra_info['data'][work['courseware_id']][str(work['content']['leaf_id'])])
                    work['problem_count'] = work['total']
            show_works(res_works, console)
            index = int(console.input("请选择你要导出数据的作业: ")) - 1
            if index > len(res_works):
                console.log("输入错误，请重新输入")
                continue
            # 判断作业的类型
            if res_works[index]['type'] == 20:
                try:
                    work_id = res_works[index]['content']['leaf_type_id']
                    work_name = res_works[index]['title']
                except Exception as e:
                    console.log(f"发生了一些错误,错误信息:{e}")
                    continue
                res = rain.get_token_work_2(course_id, work_id)
                if res['success'] is False:
                    console.log("获取token失败,错误信息:", res['msg'])
                    continue
                # 根据获取的token进入考试
                rain.get_exam_work_token_2(work_id, res['data']['user_id'], res['data']['token'], 'zh')

                res_answer = rain.get_all_answer(work_id)

                res_question = rain.get_all_question(work_id)
                if res_answer is None:
                    console.log("获取答案失败,请检查是否可以查看试卷")
                    continue
                dateToJsonFile(res_answer, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试答案"},
                               "exam",
                               f"{work_id}_answer")
                console.log(f"保存答案成功：/exam/{work_id}_answer.json")

                if res_question['data'] == {}:
                    console.log("获取题目失败,请检查是否可以查看试卷")
                    continue
                dateToJsonFile(res_question, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试题目"},
                               "exam", f"{work_id}_question")
                console.log(f"保存题目成功：/exam/{work_id}_question.json")
            elif res_works[index]['type'] == 5:
                try:
                    work_id = res_works[index]['courseware_id']
                    work_name = res_works[index]['title']
                except Exception as e:
                    console.log(f"发生了一些错误,错误信息:{e}")
                    continue
                res = rain.get_token_work(course_id, work_id)
                if res['success'] is False:
                    console.log("获取token失败,错误信息:", res['msg'])
                    continue

                # 根据获取的token进入考试
                rain.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')

                res_answer = rain.get_all_answer(work_id)

                res_question = rain.get_all_question(work_id)
                if res_answer is None:
                    console.log("获取答案失败,请检查是否可以查看试卷")
                    continue

                dateToJsonFile(res_answer, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试答案"},
                               "exam",
                               f"{work_id}_answer")
                console.log(f"保存答案成功：/exam/{work_id}_answer.json")

                if res_question['data'] == {}:
                    console.log("获取题目失败,请检查是否可以查看试卷")
                    continue
                dateToJsonFile(res_question, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试题目"},
                               "exam", f"{work_id}_question")
                console.log(f"保存题目成功：/exam/{work_id}_question.json")
            else:
                console.log(f"不支持的作业类型{res_works[index]['type']}")
        elif choose == "8":
            return
        elif choose == "9":
            user_list = get_files_in_directory("user")
            show_user(user_list, console)
            index = console.input("请选择用户: ")
            rain.user_name = user_list[int(index) - 1]['name']
            SessionManager.manage_session(rain.sees, "user", f"{rain.user_name}.json")
            continue
        elif choose == "10":
            exam_list = get_exam_files("exam")
            show_exam_file(exam_list, console)
            choose = console.input("请选择你要导出的试卷: ")
            exam_id = exam_list[int(choose) - 1]['name']
            export_excel(exam_id, exam_list[int(choose) - 1]['exam_name'])
            continue
        elif choose == "11":
            res = rain.get_course_list()
            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']
            course_sign = rain.get_course_sign(course_id)
            all_chapter = rain.get_all_chapter(course_id, course_sign)
            show_task_handle(console, all_chapter['data'], rain, course_id,is_export_answer=False)
        elif choose == "12":
            res = rain.get_course_list()
            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']
            course_sign = rain.get_course_sign(course_id)
            all_chapter = rain.get_all_chapter(course_id, course_sign)
            show_task_handle(console, all_chapter['data'], rain, course_id,is_export_answer=True)

        else:
            console.print("输入错误，请重新输入")
            select_menu(console, rain)
        choose = console.input("继续选择请输入任意键,退出请输入q:  ")
        if choose == "q":
            break
