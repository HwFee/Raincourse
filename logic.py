import time
from rich.console import Console

from api.api import RainAPI
from utils.exam import do_work, ai_do_work
from utils.export_data_excel import export_excel
from utils.seesion_io import SessionManager
from utils.ui import show_menu, show_course, show_works, show_all_answer_file, show_user, show_exam_file

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
            show_works(res, console)
            index = console.input("请输入你要选择的作业: ")
            work_id = res[int(index) - 1]['courseware_id']

            work_name = res[int(index) - 1]['title']
            res = rain.get_token_work(course_id, work_id)

            # 根据获取的token进入考试
            rain.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')

            # 获取试题（不带答案）
            res = rain.get_all_question(work_id)
            if res is None:
                console.log("获取题目失败,请检查是否可以查看试卷")
                continue
            dateToJsonFile(res, {"exam_id": work_id, "exam_name": work_name, "exam_type": "考试试题"}, "answer",
                           f"{work_id}_questions")
            console.log(f"保存试题成功：/answer/{work_id}_questions.json")
        elif choose == "4":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_work(course_id)['data']['activities']
            show_works(res, console)
            index = console.input("请输入你要选择的作业: ")
            work_id = res[int(index) - 1]['courseware_id']

            console.log("正在初始化考试状态...")
            rain.init_exam(course_id, work_id)

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
        # 导出答案
        elif choose == "6":
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
        elif choose == "7":
            return
        elif choose == "8":
            user_list = get_files_in_directory("user")
            show_user(user_list, console)
            index = console.input("请选择用户: ")
            rain.user_name = user_list[int(index) - 1]['name']
            SessionManager.manage_session(rain.sees, "user", f"{rain.user_name}.json")
            continue
        elif choose == "9":
            exam_list = get_exam_files("exam")
            show_exam_file(exam_list, console)
            choose = console.input("请选择你要导出的试卷: ")
            exam_id = exam_list[int(choose) - 1]['name']
            export_excel(exam_id, exam_list[int(choose) - 1]['exam_name'])
            continue
        elif choose == "A":
            res = rain.get_course_list()

            show_course(res['data']['list'], console)
            index = console.input("请输入你要选择的课程: ")
            course_id = res['data']['list'][int(index) - 1]['classroom_id']

            res = rain.get_work(course_id)['data']['activities']
            show_works(res, console)
            index = console.input("请输入你要选择的作业: ")
            work_id = res[int(index) - 1]['courseware_id']

            console.log("正在初始化考试状态...")
            rain.init_exam(course_id, work_id)

            res = rain.get_token_work(course_id, work_id)

            rain.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')

            console.log("获取已完成的问题")
            cache_work = rain.get_cache_work(work_id)

            console.log("获取全部的试题")
            all_question = rain.get_all_question(work_id)
            try:
                ai_do_work(console, rain, cache_work, all_question, work_id)
            except KeyError as e:
                console.log(f"获取题目失败,请检查是否已经提交，如果还未开始答题，请在手机端先点击开始答题 :{e}")
                continue

        else:
            console.print("输入错误，请重新输入")
            select_menu(console, rain)
        choose = console.input("继续选择请输入任意键,退出请输入q:  ")
        if choose == "q":
            break
