import json
import os
import time
from functools import cache
from typing import List, Dict, Any, Optional

import requests

from utils.ws_login import WebSocketClient


class RainAPI:
    def __init__(self, console):
        self.sees = requests.Session()
        self.ua = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/58.0.3029.110 Safari/537.3")

        self.console = console
        self.user_name = None

        self.init()

    def _get_cookie(self, name: str) -> Optional[str]:
        """安全获取cookie值，避免重复cookie名称的问题"""
        try:
            cookies = self.sees.cookies.get_dict()
            return cookies.get(name)
        except Exception:
            # 如果有多个同名cookie，使用last_cookie属性
            for key, value in self.sees.cookies.items():
                if key == name:
                    return value
            return None

    def init(self):
        url = "https://changjiang.yuketang.cn/web"

        res = self.sees.get(url, headers={"User-Agent": self.ua})
        if res.status_code == 200:
            self.console.log("[green]网站初始化访问成功[/green]")
        else:
            self.console.log("[red]网站初始化访问失败[/red]")

    def login(self):
        """websocket登录"""
        self.console.log("[green]开始登录[/green]")
        uri = "wss://changjiang.yuketang.cn/wsapp/"
        client = WebSocketClient(uri, self.sees.headers, self.console, self.get_token)
        try:
            client.start()
        except KeyboardInterrupt:
            self.console.log("[red]用户中断[/red]")
            client.stop()

    def get_token(self, user_id, auth):
        url = "https://changjiang.yuketang.cn/pc/web_login"
        res = self.sees.post(url, data=json.dumps({"UserID": user_id, "Auth": auth}))
        if res.status_code == 200:
            self.console.log("[green]获取登录凭证成功[/green]")
        else:
            self.console.log("[red]获取登录凭证失败[/red]")

    def get_user_info(self):
        """
        获取用户信息
        :return:
        """
        url = "https://changjiang.yuketang.cn/v2/api/web/userinfo"
        headers = {
            "User-Agent": self.ua,
            "Referer": "https://changjiang.yuketang.cn/",
        }
        response = self.sees.get(url, headers=headers)

        return response.json()

    def get_course_list(self):
        """
        获取课程列表
        :return:
        """
        url = "https://changjiang.yuketang.cn/v2/api/web/courses/list?identity=2"
        headers = {
            "User-Agent": self.ua,
            "Referer": "https://changjiang.yuketang.cn/",
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_work(self, course_id):
        """
        获取课程测试题
        :return:
        """
        url = f"https://changjiang.yuketang.cn/v2/api/web/logs/learn/{course_id}?actype=5&page=0&offset=20&sort=-1"
        headers = {
            "User-Agent": self.ua,
            "Referer": "https://changjiang.yuketang.cn/",
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_pub_new_prob(self, classroom_id: str, work_id: str):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/course/pub_new_pro"
        headers = {
            "User-Agent": self.ua,
            "Accept-Encoding": "gzip, deflate, zstd",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang-exam.yuketang.cn",
            "Pragma": "no-cache",
            "Accept": "application/json, text/plain, */*",
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Xtbz": "ykt",
            "classroom-id": str(classroom_id),
            "xt-agent": "web"
        }
        body = {
            "cid": classroom_id,
            "new_id": [work_id]
        }
        response = self.sees.post(url, headers=headers, data=json.dumps(body))
        return response.json()

    def post_test(self, exam_id: str, record: list, answer):
        """
        提交测试题
        :return:
        """
        url = f"https://changjiang-exam.yuketang.cn/exam_room/answer_problem"
        headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang-exam.yuketang.cn",
            "Pragma": "no-cache",
            "Referer": f"https://changjiang-exam.yuketang.cn/exam/{exam_id}?isFrom=2",
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "cloud"
        }

        data = {
            "results": answer,
            "exam_id": int(exam_id),
            "record": record
        }
        # Use json parameter to pass JSON data
        response = self.sees.post(url, headers=headers, json=data)
        # 设置响应编码为 UTF-8
        response.encoding = 'utf-8'
        return response.json()

    def get_exam_cover(self, classroom_id: str, exam_id: str):
        url = f"https://changjiang.yuketang.cn/v/exam/cover?exam_id={exam_id}&classroom_id={classroom_id}"
        headers = {
            "User-Agent": self.ua,
            "Referer": f"https://changjiang-exam.yuketang.cn/exam/{exam_id}?isFrom=2",
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_all_answer(self, exam_id):
        url = f"https://changjiang-exam.yuketang.cn/exam_room/problem_results?exam_id={exam_id}"

        headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang-exam.yuketang.cn",
            "Pragma": "no-cache",
            "Referer": f"https://changjiang-exam.yuketang.cn/exam/{exam_id}?isFrom=2",
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "cloud"
        }

        response = self.sees.get(url, headers=headers)
        try:
            return response.json()
        except json.decoder.JSONDecodeError:
            return None

    def get_all_question(self, exam_id):
        """
        获取所有测试题
        :return:
        """
        url = f"https://changjiang-exam.yuketang.cn/exam_room/show_paper?exam_id={exam_id}"
        headers = {
            "User-Agent": self.ua,
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip, deflate, zstd",
            "Content-Type": "application/json",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang-exam.yuketang.cn",
            "Pragma": "no-cache",
            "Referer": f"https://changjiang-exam.yuketang.cn/exam/{exam_id}?isFrom=2",
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "cloud"
        }

        response = self.sees.get(url, headers=headers)

        return response.json()

    def get_cache_work(self, work_id):
        url = f"https://changjiang-exam.yuketang.cn/exam_room/cache_results?exam_id={work_id}"
        headers = {
            "User-Agent": self.ua,
            "Referer": "https://changjiang.yuketang.cn/",
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def init_exam(self, course_id, work_id):
        url = f"https://changjiang.yuketang.cn/v2/web/trans/{course_id}/{work_id}?status=1"
        headers = {
            "User-Agent": self.ua,
            "Referer": "https://changjiang.yuketang.cn/",
        }

        response = self.sees.get(url, headers=headers, allow_redirects=True)
        if response.status_code == 200:
            self.console.log("[green]初始化测试题成功[/green]")
        else:
            self.console.log("[red]初始化测试题失败[/red]")

    def get_token_work_2(self, course_id, work_id):
        url = f"https://changjiang.yuketang.cn/v/exam/gen_token"
        headers = {
            "User-Agent": self.ua,
            "Referer": f"https://changjiang.yuketang.cn/v2/web/trans/{course_id}/{work_id}?status=4",
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Xtbz": "ykt",
            "classroom-id": str(course_id),
            "xt-agent": "web"
        }
        response = self.sees.post(url, headers=headers,
                                  data=json.dumps({"exam_id": work_id, "classroom_id": str(course_id)}))
        return response.json()

    def get_token_work(self, course_id, work_id):
        url = f"https://changjiang.yuketang.cn/v/exam/gen_token"
        headers = {
            "User-Agent": self.ua,
            "Referer": f"https://changjiang.yuketang.cn/v2/web/trans/{course_id}/{work_id}?status=1",
            "X-Csrftoken": self._get_cookie("csrftoken"),
        }
        response = self.sees.post(url, headers=headers,
                                  data=json.dumps({"exam_id": work_id, "classroom_id": str(course_id)}))
        return response.json()

    def get_trans(self, course_id, work_id):
        url = f"https://changjiang.yuketang.cn/v2/web/trans/{course_id}/{work_id}?status=4"
        headers = {
            "User-Agent": self.ua,
        }
        # 允许重定向
        response = self.sees.get(url, headers=headers, allow_redirects=True)
        print(response.text)

    def get_exam_work_token(self, work_id, user_id, token, language):
        """
        获取测试题token
        :param work_id:
        :param user_id:
        :param token:
        :param language:
        :return:
        """
        url = f"https://changjiang-exam.yuketang.cn/login"
        headers = {
            "User-Agent": self.ua,
        }
        res = self.sees.get(url, headers=headers, params={"exam_id": work_id, "user_id": user_id, "crypt": token,
                                                          "next": f"https://changjiang-exam.yuketang.cn/exam/{work_id}?isFrom=2",
                                                          "language": language}, allow_redirects=True)
        if res.status_code == 200:
            self.console.log("[green]获取测试题token成功[/green]")
        else:
            self.console.log("[red]获取测试题token失败[/red]")

    def get_exam_work_token_2(self, work_id, user_id, token, language):
        """
        获取测试题token
        :param work_id:
        :param user_id:
        :param token:
        :param language:
        :return:
        """
        url = f"https://changjiang-exam.yuketang.cn/login"
        headers = {
            "User-Agent": self.ua,
        }
        res = self.sees.get(url, headers=headers, params={"exam_id": work_id, "user_id": user_id, "crypt": token,
                                                          "next": f"https://changjiang-exam.yuketang.cn/exam/{work_id}?isFrom=2",
                                                          "language": language}, allow_redirects=True)

        if res.status_code == 200:
            self.console.log("[green]获取测试题token成功[/green]")
        else:
            self.console.log("[red]获取测试题token失败[/red]")

    def get_ppt_questions_answer(self, class_id, ppt_id):

        url = f"https://changjiang.yuketang.cn/v2/api/web/cards/detlist/{ppt_id}?classroom_id={class_id}"
        headers = {
            "User-Agent": self.ua,
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_status(self, leaf_id, class_id):
        url = f"https://changjiang.yuketang.cn/v/discussion/v2/student/comment/status/?leaf_id={leaf_id}&classroom_id={class_id}&term=latest&uv_id={self.sees.cookies.get('uv_id')}"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_all_chapter(self, class_id, course_sign):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/course/chapter?cid={class_id}&sign={course_sign['data']['course_sign']}&term=latest&uv_id={self.sees.cookies.get('uv_id')}"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }
        response = self.sees.get(url, headers=headers)
        return response.json()

    def get_course_sign(self, class_id):
        url = f"https://changjiang.yuketang.cn/v2/api/web/classrooms/{class_id}?role=5"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }
        response = self.sees.get(
            url=url,
            headers=headers
        )
        return response.json()

    def get_leaf_info(self, leaf_id, class_id, course_sign):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/leaf_info/{class_id}/{leaf_id}/?sign={course_sign}&term=latest&uv_id={self.sees.cookies.get('uv_id')}"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }
        response = self.sees.get(
            url=url,
            headers=headers
        )
        return response.json()

    def get_discussion_info(self, leaf_id, class_id, sku_id, topic_type):
        timestamp_ms = str(int(time.time() * 1000))
        url = f"https://changjiang.yuketang.cn/v/discussion/v2/unit/discussion/?_date={timestamp_ms}&term=latest&classroom_id={class_id}&sku_id={sku_id}&leaf_id={leaf_id}&topic_type={topic_type}&channel=xt"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }
        response = self.sees.get(
            url=url,
            headers=headers
        )
        return response.json()

    def read_announcement(self, leaf_id, class_id, sku_id):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/learn/user_article_finish/{leaf_id}/?cid={class_id}&sid={sku_id}&term=latest&uv_id={self.sees.cookies.get('uv_id')}"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }

        response = self.sees.get(
            url=url,
            headers=headers
        )
        return response.json()

    def post_comment(self, class_id, user_id, topic_id, answer, course_sign, leaf_id):
        url = f"https://changjiang.yuketang.cn/v/discussion/v2/comment/?term=latest&uv_id={self.sees.cookies.get('university_id')}"
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'classroom-id': str(class_id),
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://changjiang.yuketang.cn',
            'priority': 'u=1, i',
            'referer': f'https://changjiang.yuketang.cn/pro/lms/{course_sign}/{class_id}/forum/{leaf_id}',
            "Cookie": f"csrftoken={self.sees.cookies.get('csrftoken')};classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            'sec-ch-ua': '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
            'university-id': str(self.sees.cookies.get('university_id')),
            "X-Csrftoken": self._get_cookie("csrftoken"),
            'xt-agent': 'web',
            'xtbz': 'ykt',
        }

        data = {"to_user": user_id, "topic_id": topic_id,
                "content": {"text": answer, "upload_images": [], "accessory_list": []}, "anchor": 0}
        response = self.sees.post(
            url=url,
            headers=headers,
            data=json.dumps(data)
        )
        return response.json()

    def post_work_answer(self, leaf_id, class_id, course_sign, answer, problem_id):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/exercise/problem_apply/?term=latest&uv_id={self.sees.cookies.get('university_id')}"

        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://changjiang.yuketang.cn',
            'priority': 'u=1, i',
            'referer': f'https://changjiang.yuketang.cn/pro/lms/{course_sign}/{class_id}/homework/{leaf_id}',
            "Cookie": f"csrftoken={self.sees.cookies.get('csrftoken')};sessionid={self.sees.cookies.get('sessionid')}",
            'sec-ch-ua': '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
            'university-id': str(self.sees.cookies.get('university_id')),
            "X-Csrftoken": self._get_cookie("csrftoken"),
            'xt-agent': 'web',
            'xtbz': 'ykt',
        }

        data = {"classroom_id": class_id, "problem_id": problem_id, "answer": answer}
        response = self.sees.post(
            url=url,
            headers=headers,
            data=json.dumps(data)
        )
        return response.json()

    def post_ppt_answer(self, class_id, answer_id, answer_content):
        url = "https://changjiang.yuketang.cn/v2/api/web/cards/problem_result"
        headers = {
            "User-Agent": self.ua,
            "X-Csrftoken": self._get_cookie("csrftoken"),
            "Sec-Ch-Ua": "\"Microsoft Edge\";v=\"125\", \"Chromium\";v=\"125\", \"Not.A/Brand\";v=\"24\"",
            "Sec-Ch-Ua-Mobile": "?0",
            "Cookie": f"classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            "Sec-Ch-Ua-Platform": "\"Windows\"",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Client": "web",
            "Xtbz": "ykt",
            "Classroom-Id": str(class_id),
            "Content-Type": "application/json;charset=UTF-8",
            "Cache-Control": "no-cache",
            "Origin": "https://changjiang.yuketang.cn",
            "Pragma": "no-cache"
        }

        data = {
            "cards_problem_id": answer_id,
            "classroom_id": str(class_id),
            "duration": 12,
            "result": answer_content,
        }

        response = self.sees.post(url, headers=headers, data=json.dumps(data))
        return response.json()

    def get_exercise_list(self, class_id, leaf_id, sku_id):
        url = f"https://changjiang.yuketang.cn/mooc-api/v1/lms/exercise/get_exercise_list/{leaf_id}/{sku_id}/?term=latest&uv_id={self.sees.cookies.get('university_id')}"
        headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'classroom-id': str(class_id),
            'content-type': 'application/json;charset=UTF-8',
            'origin': 'https://changjiang.yuketang.cn',
            'priority': 'u=1, i',
            # 'referer': f'https://changjiang.yuketang.cn/pro/lms/{course_sign}/{class_id}/forum/{leaf_id}',
            "Cookie": f"csrftoken={self.sees.cookies.get('csrftoken')};classroom_id={class_id};classroomId={class_id};sessionid={self.sees.cookies.get('sessionid')}",
            'sec-ch-ua': '"Microsoft Edge";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0',
            'university-id': str(self.sees.cookies.get('university_id')),
            "X-Csrftoken": self._get_cookie("csrftoken"),
            'xt-agent': 'web',
            'xtbz': 'ykt',
        }

        response = self.sees.get(url, headers=headers)
        return response.json()

