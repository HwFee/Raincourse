"""
AI - GUI
 - 
"""
import webview
import json
import threading
import os
import re
import sys
import base64
import io
import traceback
from threading import Event
from api.api import RainAPI
from utils.seesion_io import SessionManager
from utils.exam import ai_do_work
from utils.utils import get_project_root
from utils.api_config_manager import APIConfigManager
from utils.question_exporter import QuestionExporter
from rich.console import Console
import time


DEBUG_LOG_PATH = os.path.join(get_project_root(), "logs", "gui_backend_debug.log")


def debug_log(message):
    """将关键流程日志写入固定文件，避免无终端场景下丢日志。"""
    try:
        os.makedirs(os.path.dirname(DEBUG_LOG_PATH), exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def _ensure_stdio_for_windowed_mode():
    """在 pythonw 无控制台模式下，为 stdout/stderr 提供可写目标。"""
    try:
        log_path = os.path.join(get_project_root(), "logs", "gui_runtime.log")
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        log_stream = open(log_path, "a", encoding="utf-8", buffering=1)

        if sys.stdout is None:
            sys.stdout = log_stream
        if sys.stderr is None:
            sys.stderr = log_stream
    except Exception:
        # 即使日志初始化失败，也不要阻断 GUI 启动
        pass


_ensure_stdio_for_windowed_mode()
debug_log(f"GUI process started, cwd={os.getcwd()}")

# 
current_user = None
rain_api = None
BASE_DIR = get_project_root()
answer_thread = None
answer_stop_event = Event()
is_answering = False  # 
api_config_manager = APIConfigManager()  # API
question_exporter = QuestionExporter()  # 


def emit_frontend_log(message, log_type="info"):
    """将日志同步到前端面板"""
    try:
        if webview.windows:
            payload = json.dumps({"message": message, "type": log_type}, ensure_ascii=False)
            webview.windows[0].evaluate_js(f"window.handleBackendLog({payload})")
    except Exception as e:
        # 打印错误但不中断程序
        print(f"前端日志同步失败: {e}")


def call_frontend(function_name, *args):
    """安全调用前端函数，自动处理字符串转义。"""
    try:
        if not webview.windows:
            return
        js_args = ", ".join(json.dumps(arg, ensure_ascii=False) for arg in args)
        webview.windows[0].evaluate_js(f"{function_name}({js_args})")
    except Exception as e:
        debug_log(f"call_frontend error: func={function_name}, err={e}")


class GuiConsole:
    """终端和前端共用的日志控制台"""

    def __init__(self):
        self.console = Console()

    def _safe_console_text(self, text):
        """避免在 GBK 等编码下输出 emoji 触发编码异常。"""
        encoding = (getattr(sys.stdout, "encoding", None) or "").lower()
        if not encoding:
            return text
        try:
            text.encode(encoding)
            return text
        except Exception:
            return text.encode(encoding, errors="ignore").decode(encoding, errors="ignore")

    def _strip_markup(self, text):
        plain = re.sub(r'\[[^\]]+\]', '', str(text))
        return plain.replace("【", "[").replace("】", "]")

    def _guess_type(self, message):
        if "❌" in message or "失败" in message or "错误" in message:
            return "error"
        if "⚠️" in message or "警告" in message:
            return "warning"
        if "✅" in message or "成功" in message or "完成" in message:
            return "success"
        return "info"

    def log(self, message):
        plain = self._strip_markup(message)
        safe_plain = self._safe_console_text(plain)
        try:
            self.console.log(safe_plain)
        except Exception as e:
            # 无终端/pythonw 场景下，Rich 可能因编码问题写控制台失败
            debug_log(f"GuiConsole.log fallback: {e}; message={plain}")
        emit_frontend_log(plain, self._guess_type(plain))

    def print(self, *args, **kwargs):
        safe_args = tuple(self._safe_console_text(self._strip_markup(arg)) for arg in args)
        try:
            self.console.print(*safe_args, **kwargs)
        except Exception as e:
            plain_args = " ".join(self._strip_markup(arg) for arg in args) if args else ""
            debug_log(f"GuiConsole.print fallback: {e}; message={plain_args}")
        if args:
            plain = " ".join(self._strip_markup(arg) for arg in args)
            emit_frontend_log(plain, self._guess_type(plain))


console = GuiConsole()


class API:
    """API"""

    def _resolve_data_dir(self, dir_name):
        """"""
        return os.path.join(BASE_DIR, dir_name)

    def _extract_course_info(self, course):
        """"""
        nested_course = course.get('course') if isinstance(course.get('course'), dict) else {}
        teacher_info = course.get('teacher') if isinstance(course.get('teacher'), dict) else {}

        course_id = (
            course.get('classroom_id')
            or nested_course.get('classroom_id')
            or nested_course.get('id')
            or course.get('id')
            or ''
        )

        return {
            'id': str(course_id),
            'classroom_id': str(course_id),
            'name': (
                nested_course.get('name')
                or course.get('name')
                or course.get('course_name')
                or ''
            ),
            'teacher': teacher_info.get('name', ''),
            'student_count': course.get('student_count', nested_course.get('student_count', 0)),
        }

    def _extract_work_info(self, work):
        """"""
        content = work.get('content') if isinstance(work.get('content'), dict) else {}
        raw_status = work.get('status')
        completed = work.get('completed')
        work_type = work.get('type')

        if completed is True:
            status_text = ''
        elif completed is False:
            status_text = ''
        elif raw_status is None:
            status_text = ''
        else:
            status_text = str(raw_status)

        courseware_id = work.get('courseware_id') or work.get('id') or ''
        leaf_type_id = content.get('leaf_type_id') or ''

        # type=20 的考试活动，真正用于答题接口的 exam_id 通常是 leaf_type_id
        if work_type == 20 and leaf_type_id:
            work_id = leaf_type_id
        else:
            work_id = courseware_id or leaf_type_id or ''

        return {
            'id': str(work_id),
            'courseware_id': str(courseware_id or work_id),
            'leaf_type_id': str(leaf_type_id),
            'title': work.get('title') or work.get('name') or '',
            'type': work_type if work_type is not None else '',
            'status': status_text,
            'score': work.get('score'),
            'problem_count': work.get('problem_count', work.get('total')),
        }

    def check_login(self):
        """"""
        global current_user, rain_api
        
        print(" ...")
        
        # 
        if not current_user:
            users = self.get_saved_users()
            if users:
                # 
                print(f" : {users[0]}")
                result = self.load_user_session(users[0])
                if not result['success']:
                    print(f" : {result['message']}")
        
        print(f"{' ' if current_user else ' '}: {current_user or ''}")
        
        return {
            'logged_in': current_user is not None,
            'username': current_user
        }

    def get_saved_users(self):
        """"""
        try:
            user_dir = self._resolve_data_dir("user")
            print(f" : {user_dir}")
            
            if not os.path.exists(user_dir):
                os.makedirs(user_dir, exist_ok=True)
                print(f" : {user_dir}")
                return []

            users = []
            for filename in sorted(os.listdir(user_dir)):
                if filename.endswith('.json'):
                    username = filename.replace('.json', '')
                    users.append(username)
                    print(f"  - : {username}")

            print(f"  {len(users)} ")
            return users
        except Exception as e:
            print(f" : {e}")
            import traceback
            traceback.print_exc()
            return []

    def load_user_session(self, username):
        """"""
        try:
            global rain_api, current_user
            print(f" : {username}")
            
            rain_api = RainAPI(console=console)
            session_path = SessionManager.get_full_path("user", f"{username}.json")
            if not os.path.exists(session_path):
                return {
                    'success': False,
                    'message': f': {username}'
                }

            SessionManager.load_session(rain_api.sees, session_path)
            print(f" Session")

            # 
            user_info = rain_api.get_user_info()
            print(f" : {user_info}")
            
            if user_info and 'data' in user_info and len(user_info['data']) > 0:
                current_user = user_info['data'][0]['name']
                print(f" : {current_user}")

                return {
                    'success': True,
                    'message': f': {current_user}',
                    'username': current_user
                }
            else:
                print(f" ")
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            print(f" : {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def start_qr_login(self):
        """"""
        try:
            global rain_api, current_user
            debug_log("start_qr_login called")

            # API
            rain_api = RainAPI(console=console)

            # 
            def login_thread():
                try:
                    import websocket
                    import json
                    debug_log("qr login thread started")

                    console.log("...")
                    
                    uri = "wss://changjiang.yuketang.cn/wsapp/"
                    ws_headers = [f"{k}: {v}" for k, v in rain_api.sees.headers.items()]

                    def on_message(ws, message):
                        try:
                            response = json.loads(message)
                        except Exception:
                            debug_log(f"qr on_message json parse failed: {message[:120]}")
                            return

                        if 'qrcode' in response:
                            qr_data = response.get('qrcode', '')
                            debug_log(f"qr received, length={len(qr_data)}")
                            try:
                                from qrcode import QRCode

                                qr = QRCode(box_size=8, border=2)
                                qr.add_data(qr_data)
                                qr.make(fit=True)
                                image = qr.make_image(fill_color="black", back_color="white")
                                buffer = io.BytesIO()
                                image.save(buffer, format='PNG')
                                qr_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                                call_frontend("showQRCodeImage", f"data:image/png;base64,{qr_base64}")
                            except Exception as e:
                                # Pillow 不可用时，使用 SVG 工厂生成二维码图片（不依赖 PIL）
                                debug_log(f"qr png render failed, fallback to svg: {e}")
                                try:
                                    import qrcode
                                    from qrcode.image.svg import SvgPathImage

                                    svg_qr = qrcode.QRCode(box_size=8, border=2, image_factory=SvgPathImage)
                                    svg_qr.add_data(qr_data)
                                    svg_qr.make(fit=True)
                                    svg_img = svg_qr.make_image()
                                    svg_buffer = io.BytesIO()
                                    svg_img.save(svg_buffer)
                                    svg_base64 = base64.b64encode(svg_buffer.getvalue()).decode('utf-8')
                                    call_frontend("showQRCodeImage", f"data:image/svg+xml;base64,{svg_base64}")
                                except Exception as svg_e:
                                    # 最后兜底才显示文本
                                    debug_log(f"qr svg render failed, fallback to text: {svg_e}")
                                    call_frontend("showQRCode", qr_data)

                            console.log("")

                        elif response.get('subscribe_status') is True:
                            # 
                            user_id = response.get('UserID')
                            auth = response.get('Auth')
                            debug_log(f"qr subscribe_status true, user_id={user_id}")
                            if not user_id or not auth:
                                call_frontend("handleLoginError", "登录回调缺少必要字段")
                                return
                            
                            # token
                            url = "https://changjiang.yuketang.cn/pc/web_login"
                            login_resp = rain_api.sees.post(url, data=json.dumps({"UserID": user_id, "Auth": auth}))
                            debug_log(f"pc/web_login status={login_resp.status_code}")
                            
                            # 
                            user_info = rain_api.get_user_info()
                            if user_info and 'data' in user_info and len(user_info['data']) > 0:
                                current_user = user_info['data'][0]['name']
                                # session
                                SessionManager.manage_session(rain_api.sees, "user", f"{current_user}.json")
                                console.log(f"{current_user}")
                                
                                # 
                                call_frontend("handleLoginSuccess", current_user)
                            else:
                                debug_log(f"get_user_info failed after qr login: {user_info}")
                                call_frontend("handleLoginError", "登录成功但获取用户信息失败")
                            
                            ws.close()

                    def on_error(ws, error):
                        debug_log(f"qr websocket error: {error}")
                        call_frontend("handleLoginError", f"二维码连接失败: {error}")

                    def on_close(ws, close_status_code, close_msg):
                        debug_log(f"qr websocket closed: code={close_status_code}, msg={close_msg}")
                    
                    def on_open(ws):
                        # 
                        message = {
                            "op": "requestlogin",
                            "role": "web",
                            "version": 1.4,
                            "type": "qrcode",
                            "from": "web"
                        }
                        debug_log("qr websocket opened, sending requestlogin")
                        ws.send(json.dumps(message))
                    
                    # WebSocket
                    ws = websocket.WebSocketApp(
                        uri,
                        header=ws_headers,
                        on_open=on_open,
                        on_message=on_message,
                        on_error=on_error,
                        on_close=on_close,
                    )
                    ws.run_forever()
                    
                except Exception as e:
                    debug_log(f"qr login thread exception: {traceback.format_exc()}")
                    console.log(f": {str(e)}")
                    # 
                    call_frontend("handleLoginError", str(e))

            # 
            thread = threading.Thread(target=login_thread)
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'message': '...'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def get_courses(self):
        """"""
        try:
            if not rain_api:
                print(" rain_api ")
                return {
                    'success': False,
                    'message': ''
                }

            print(" ...")
            res = rain_api.get_course_list()
            print(f" : {json.dumps(res, ensure_ascii=False, indent=2)}")
            
            if res and 'data' in res:
                # 
                course_list = None
                if 'list' in res['data']:
                    course_list = res['data']['list']
                elif 'courseList' in res['data']:
                    course_list = res['data']['courseList']
                else:
                    print(f" : {res['data'].keys()}")
                    return {
                        'success': False,
                        'message': ''
                    }
                
                courses = []
                for course in course_list:
                    course_info = self._extract_course_info(course)
                    courses.append(course_info)
                    print(f"  - : {course_info['name']} (ID: {course_info['id']})")

                print(f"  {len(courses)} ")
                return {
                    'success': True,
                    'courses': courses
                }
            else:
                print(f" : {res}")
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            print(f" : {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def get_works(self, course_id):
        """"""
        try:
            if not rain_api:
                print(" rain_api ")
                return {
                    'success': False,
                    'message': ''
                }

            print(f"  {course_id} ...")
            res = rain_api.get_work(course_id)
            print(f" : {json.dumps(res, ensure_ascii=False, indent=2)}")
            
            if res and 'data' in res:
                data = res['data']
                activities = data.get('activities') or data.get('list') or []
                
                if not activities:
                    print(f" ")
                    return {
                        'success': True,
                        'works': []
                    }
                
                works = []
                for work in activities:
                    work_info = self._extract_work_info(work)
                    works.append(work_info)
                    print(f"  - : {work_info['title']} (ID: {work_info['id']})")

                print(f"  {len(works)} ")
                return {
                    'success': True,
                    'works': works
                }
            else:
                print(f" : {res}")
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            print(f" : {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def start_ai_answer(self, course_id, work_id):
        """开始AI答题"""
        try:
            global is_answering, answer_stop_event
            debug_log(f"start_ai_answer called: course_id={course_id}, work_id={work_id}, has_rain_api={bool(rain_api)}")
            
            if not rain_api:
                return {
                    'success': False,
                    'message': '请先登录'
                }
            
            if is_answering:
                return {
                    'success': False,
                    'message': '正在答题中,请先停止当前答题'
                }

            # 重置停止事件
            answer_stop_event.clear()
            is_answering = True

            # 在新线程中执行答题
            def answer_thread_func():
                global is_answering
                try:
                    resolved_work_id = str(work_id)
                    resolved_work_type = None
                    resolved_courseware_id = None
                    debug_log(f"answer_thread started with initial work_id={resolved_work_id}")

                    # 反查当前活动类型，兼容 type=20 的 work_id 解析与取 token 方式
                    try:
                        works_res = rain_api.get_work(course_id)
                        activities = (works_res.get('data') or {}).get('activities') or []
                        debug_log(f"get_work success, activities_count={len(activities)}")
                        for item in activities:
                            content = item.get('content') if isinstance(item.get('content'), dict) else {}
                            courseware_id = str(item.get('courseware_id') or item.get('id') or '')
                            leaf_type_id = str(content.get('leaf_type_id') or '')
                            if str(work_id) in {courseware_id, leaf_type_id}:
                                resolved_work_type = item.get('type')
                                resolved_courseware_id = courseware_id
                                if resolved_work_type == 20 and leaf_type_id:
                                    resolved_work_id = leaf_type_id
                                elif courseware_id:
                                    resolved_work_id = courseware_id
                                break
                    except Exception:
                        debug_log(f"resolve work type failed: {traceback.format_exc()}")

                    debug_log(
                        f"resolved work: work_id={resolved_work_id}, "
                        f"work_type={resolved_work_type}, courseware_id={resolved_courseware_id}"
                    )

                    if resolved_work_type == 20:
                        # 部分考试活动需要先触发 pub_new_pro 才能顺利拿到 token
                        if resolved_courseware_id:
                            try:
                                rain_api.get_pub_new_prob(course_id, resolved_courseware_id)
                            except Exception:
                                debug_log(f"get_pub_new_prob failed (ignored): {traceback.format_exc()}")

                        res = rain_api.get_token_work_2(course_id, resolved_work_id)
                        debug_log(f"get_token_work_2 response keys: {list(res.keys()) if isinstance(res, dict) else type(res)}")
                        if not res or 'data' not in res:
                            raise RuntimeError('获取考试token失败，请先在雨课堂页面进入该考试并点击开始答题')

                        rain_api.get_exam_work_token_2(
                            resolved_work_id,
                            res['data']['user_id'],
                            res['data']['token'],
                            'zh'
                        )
                    else:
                        # 初始化考试状态
                        rain_api.init_exam(course_id, resolved_work_id)
                        debug_log("init_exam done")

                        # 获取token
                        res = rain_api.get_token_work(course_id, resolved_work_id)
                        debug_log(f"get_token_work response keys: {list(res.keys()) if isinstance(res, dict) else type(res)}")
                        if not res or 'data' not in res:
                            raise RuntimeError('获取考试token失败，请先在雨课堂页面进入该考试并点击开始答题')

                        # 进入考试
                        rain_api.get_exam_work_token(
                            resolved_work_id,
                            res['data']['user_id'],
                            res['data']['token'],
                            'zh'
                        )

                    # 获取已完成的问题
                    cache_work = rain_api.get_cache_work(resolved_work_id)
                    debug_log(f"get_cache_work ok: has_data={bool(cache_work and 'data' in cache_work)}")
                    if not cache_work or 'data' not in cache_work:
                        raise RuntimeError('获取考试缓存失败，请确认当前考试已开始')

                    # 获取全部试题
                    all_question = rain_api.get_all_question(resolved_work_id)
                    problem_count = 0
                    if all_question and 'data' in all_question and isinstance(all_question['data'], dict):
                        problem_count = len(all_question['data'].get('problems') or [])
                    debug_log(f"get_all_question done: problem_count={problem_count}")
                    if not all_question or 'data' not in all_question or not all_question['data'].get('problems'):
                        raise RuntimeError('获取题目失败，请先在手机端或网页端点击开始答题后再试')

                    # 读取当前API配置中的密钥（优先于 config.py）
                    provider_id = api_config_manager.configs.get('current_provider', 'minimax_token_plan')
                    current_provider = api_config_manager.get_current_provider() or {}
                    current_api_key = current_provider.get('api_key')
                    provider_type = current_provider.get('api_type')
                    debug_log(
                        f"ai provider selected: {provider_id}, type={provider_type}, "
                        f"has_api_key={bool(current_api_key)}"
                    )

                    if not provider_type:
                        raise RuntimeError('当前未选择可用模型服务商，请在设置中启用一个服务商')

                    if not current_api_key:
                        raise RuntimeError('未配置模型 API Key，请在设置 -> API配置 中配置后再试')

                    # 开始AI答题(传入停止事件)
                    ai_do_work(
                        console,
                        rain_api,
                        cache_work,
                        all_question,
                        resolved_work_id,
                        stop_event=answer_stop_event,
                        api_key=current_api_key,
                        provider_config=current_provider,
                    )
                    debug_log("ai_do_work finished")

                    # 通知前端答题完成
                    if not answer_stop_event.is_set():
                        webview.windows[0].evaluate_js(
                            'handleAnswerComplete("答题完成！")'
                        )
                    else:
                        webview.windows[0].evaluate_js(
                            'handleAnswerStopped("答题已手动停止")'
                        )
                except Exception as e:
                    debug_log(f"answer_thread exception: {str(e)} | traceback={traceback.format_exc()}")
                    # 通知前端答题失败
                    webview.windows[0].evaluate_js(
                        f'handleAnswerError("答题失败: {str(e)}")'
                    )
                finally:
                    is_answering = False
                    debug_log("answer_thread ended")

            # 启动答题线程
            thread = threading.Thread(target=answer_thread_func)
            thread.daemon = True
            thread.start()

            return {
                'success': True,
                'message': '开始AI答题...'
            }
        except Exception as e:
            is_answering = False
            return {
                'success': False,
                'message': f'答题出错: {str(e)}'
            }
    
    def stop_ai_answer(self):
        """停止AI答题"""
        global is_answering, answer_stop_event
        
        if not is_answering:
            return {
                'success': False,
                'message': '当前没有正在进行的答题'
            }
        
        # 设置停止标志
        answer_stop_event.set()
        is_answering = False
        
        console.log("⏹️ 已发送停止信号,正在停止答题...")
        
        return {
            'success': True,
            'message': '已发送停止信号'
        }
    
    def get_answer_status(self):
        """获取答题状态"""
        return {
            'is_answering': is_answering
        }

    def get_files(self, file_type):
        """"""
        try:
            print(f"  {file_type} ...")
            
            files = []
            
            if file_type == 'question':
                # exam
                dir_path = self._resolve_data_dir('exam')
                if os.path.exists(dir_path):
                    for filename in sorted(os.listdir(dir_path)):
                        if not filename.endswith('.json'):
                            continue
                        
                        if not filename.endswith('_question.json'):
                            continue

                        file_path = os.path.join(dir_path, filename)
                        file_stat = os.stat(file_path)
                        display_name = filename
                        description = ''

                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_data = json.load(f)
                            info = file_data.get('info', {})
                            display_name = info.get('exam_name') or filename
                            description = f"ID: {info.get('exam_id', '')} | "
                        except Exception:
                            description = ""

                        files.append({
                            'name': display_name,
                            'path': file_path,
                            'description': description,
                            'raw_name': filename,
                            'size': f'{file_stat.st_size / 1024:.2f} KB',
                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_mtime)),
                            'type': 'exam'
                        })
                
                # exports
                exports_path = self._resolve_data_dir('exports')
                if os.path.exists(exports_path):
                    for filename in sorted(os.listdir(exports_path)):
                        # 
                        if not (filename.endswith('.json') or filename.endswith('.csv') or 
                               filename.endswith('.xlsx') or filename.endswith('.md')):
                            continue

                        file_path = os.path.join(exports_path, filename)
                        file_stat = os.stat(file_path)
                        
                        # 
                        ext = filename.split('.')[-1].lower()
                        format_name = {
                            'json': 'JSON',
                            'csv': 'CSV',
                            'xlsx': 'Excel',
                            'md': 'Markdown'
                        }.get(ext, ext.upper())
                        
                        files.append({
                            'name': filename,
                            'path': file_path,
                            'description': f" ({format_name})",
                            'raw_name': filename,
                            'size': f'{file_stat.st_size / 1024:.2f} KB',
                            'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_mtime)),
                            'type': 'export'
                        })
                
            elif file_type == 'user':
                dir_path = self._resolve_data_dir('user')
                if not os.path.exists(dir_path):
                    os.makedirs(dir_path, exist_ok=True)
                    print(f" : {dir_path}")
                    return {
                        'success': True,
                        'files': []
                    }

                for filename in sorted(os.listdir(dir_path)):
                    if not filename.endswith('.json'):
                        continue

                    file_path = os.path.join(dir_path, filename)
                    file_stat = os.stat(file_path)
                    display_name = filename.replace('.json', '')
                    description = ""

                    files.append({
                        'name': display_name,
                        'path': file_path,
                        'description': description,
                        'raw_name': filename,
                        'size': f'{file_stat.st_size / 1024:.2f} KB',
                        'date': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_stat.st_mtime)),
                        'type': 'user'
                    })

            # 
            files.sort(key=lambda x: x['date'], reverse=True)
            
            print(f"  {len(files)} ")
            return {
                'success': True,
                'files': files
            }
        except Exception as e:
            print(f" : {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def export_file(self, file_path):
        """打开文件所在位置"""
        try:
            # 确保文件路径存在
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': f'文件不存在: {file_path}'
                }
            
            import subprocess
            import platform
            
            if platform.system() == 'Windows':
                # Windows: 使用explorer打开并选中文件
                subprocess.Popen(['explorer', '/select,', os.path.abspath(file_path)])
            elif platform.system() == 'Darwin':  # macOS
                subprocess.Popen(['open', '-R', file_path])
            else:  # Linux
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])

            return {
                'success': True,
                'message': '已打开文件位置'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'打开失败: {str(e)}'
            }
    
    # ==================== API ====================
    
    def get_preset_providers(self):
        """"""
        try:
            providers = api_config_manager.get_preset_providers()
            return {
                'success': True,
                'providers': providers
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def get_all_providers(self):
        """"""
        try:
            providers = api_config_manager.get_all_providers()
            return {
                'success': True,
                'providers': providers,
                'current_provider_id': api_config_manager.configs.get('current_provider')
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def get_provider_config(self, provider_id):
        """"""
        try:
            config = api_config_manager.get_provider_config(provider_id)
            if config:
                # 不把明文key返回给前端，仅返回掩码
                key = config.get('api_key', '')
                config['api_key_masked'] = key[:8] + '***' + key[-4:] if len(key) > 12 else ('***' if key else '')
                config['configured'] = bool(key)
                config.pop('api_key', None)
                
                return {
                    'success': True,
                    'config': config
                }
            else:
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def set_provider_api_key(self, provider_id, api_key, base_url=None, default_model=None):
        """API"""
        try:
            success = api_config_manager.set_provider_api_key(
                provider_id, api_key, base_url, default_model
            )
            if success:
                return {
                    'success': True,
                    'message': 'API'
                }
            else:
                return {
                    'success': False,
                    'message': 'API'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }

    def set_provider_enabled(self, provider_id, enabled):
        """服务商开关（开=正在使用，关=不再使用）"""
        try:
            success = api_config_manager.set_provider_enabled(provider_id, bool(enabled))
            if success:
                return {
                    'success': True,
                    'message': '设置成功'
                }
            return {
                'success': False,
                'message': '设置失败'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def set_current_provider(self, provider_id):
        """"""
        try:
            success = api_config_manager.set_current_provider(provider_id)
            if success:
                return {
                    'success': True,
                    'message': ''
                }
            else:
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def test_api_connection(self, provider_id):
        """API"""
        try:
            result = api_config_manager.test_api_connection(provider_id)
            return result
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def add_custom_provider(self, provider_id, name, api_type, base_url, 
                           api_key=None, models=None, default_model=None, description=""):
        """"""
        try:
            success = api_config_manager.add_custom_provider(
                provider_id, name, api_type, base_url, 
                api_key, models, default_model, description
            )
            if success:
                return {
                    'success': True,
                    'message': ''
                }
            else:
                return {
                    'success': False,
                    'message': ''
                }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def remove_custom_provider(self, provider_id):
        """"""
        try:
            success = api_config_manager.remove_custom_provider(provider_id)
            if success:
                return {
                    'success': True,
                    'message': ''
                }
            else:
                return {
                    'success': False,
                    'message': '()'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    # ====================  ====================
    
    def export_questions(self, questions, format_type="json", filename=None):
        """
        
        Args:
            questions: 
            format_type:  (json/csv/excel/markdown)
            filename: ()
        """
        try:
            if format_type == "json":
                result = question_exporter.export_to_json(questions, filename)
            elif format_type == "csv":
                result = question_exporter.export_to_csv(questions, filename)
            elif format_type == "excel":
                result = question_exporter.export_to_excel(questions, filename)
            elif format_type == "markdown":
                result = question_exporter.export_to_markdown(questions, filename)
            else:
                return {
                    'success': False,
                    'message': f': {format_type}'
                }
            
            return result
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def get_export_history(self):
        """"""
        try:
            files = question_exporter.get_export_history()
            return {
                'success': True,
                'files': files
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def get_questions_from_file(self, file_path):
        """"""
        try:
            if not os.path.exists(file_path):
                return {
                    'success': False,
                    'message': ''
                }
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 
            if isinstance(data, dict):
                if 'questions' in data:
                    questions = data['questions']
                elif 'data' in data and 'problems' in data['data']:
                    questions = data['data']['problems']
                else:
                    questions = [data]
            elif isinstance(data, list):
                questions = data
            else:
                return {
                    'success': False,
                    'message': ''
                }
            
            return {
                'success': True,
                'questions': questions,
                'count': len(questions)
            }
        except Exception as e:
            return {
                'success': False,
                'message': f': {str(e)}'
            }
    
    def export_questions_from_server(self, course_id, work_id, format_type="json", filename=None):
        """"""
        try:
            if not rain_api:
                return {
                    'success': False,
                    'message': ''
                }
            
            console.log(f" ...")
            
            # 
            rain_api.init_exam(course_id, work_id)
            
            # token
            res = rain_api.get_token_work(course_id, work_id)
            
            # 
            rain_api.get_exam_work_token(work_id, res['data']['user_id'], res['data']['token'], 'zh')
            
            # 
            all_question = rain_api.get_all_question(work_id)
            
            if not all_question or 'data' not in all_question:
                return {
                    'success': False,
                    'message': ''
                }
            
            questions = all_question['data'].get('problems', [])
            
            if not questions:
                return {
                    'success': False,
                    'message': ''
                }
            
            console.log(f"  {len(questions)} ")
            
            # 
            result = self.export_questions(questions, format_type, filename)
            
            return result
        except Exception as e:
            console.log(f" : {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'message': f': {str(e)}'
            }


def create_window():
    """"""
    # API
    api = API()

    # 
    window = webview.create_window(
        title='AI',
        url=os.path.join(BASE_DIR, 'web', 'index.html'),
        js_api=api,
        width=1400,
        height=900,
        resizable=True,
        fullscreen=False,
        min_size=(1200, 800),
        background_color='#0a0a0f'
    )

    return window


if __name__ == '__main__':
    # 
    window = create_window()
    # debug,devtools
    webview.start(debug=False)
