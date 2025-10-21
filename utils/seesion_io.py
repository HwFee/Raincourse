import base64
import json
import os
import pickle
import requests

class SessionManager:
    @staticmethod
    def export_session(session):
        session_data = {
            'cookies': session.cookies.get_dict(),
            'headers': dict(session.headers),
            'auth': session.auth,
            'proxies': session.proxies,
            'hooks': session.hooks,
            'params': session.params,
            'verify': session.verify,
            'cert': session.cert,
            'adapters': session.adapters,
            'stream': session.stream,
            'trust_env': session.trust_env,
            'max_redirects': session.max_redirects,
        }

        serialized = pickle.dumps(session_data)
        return base64.b64encode(serialized).decode('utf-8')

    @staticmethod
    def import_session(session, session_string):
        serialized = base64.b64decode(session_string.encode('utf-8'))
        session_data = pickle.loads(serialized)

        session.cookies.update(session_data['cookies'])
        session.headers.update(session_data['headers'])
        session.auth = session_data['auth']
        session.proxies.update(session_data['proxies'])
        session.hooks.update(session_data['hooks'])
        session.params.update(session_data['params'])
        session.verify = session_data['verify']
        session.cert = session_data['cert']
        session.adapters = session_data['adapters']
        session.stream = session_data['stream']
        session.trust_env = session_data['trust_env']
        session.max_redirects = session_data['max_redirects']

    @staticmethod
    def get_full_path(file_path: str, filename: str) -> str:
        """获取完整的文件路径"""
        # 使用当前工作目录作为基准
        base_path = os.getcwd()
        return os.path.join(base_path, file_path, filename)

    @staticmethod
    def save_session(session, full_path: str):
        """保存当前会话到文件，如果目录不存在则创建"""
        session_data = SessionManager.export_session(session)
        directory = os.path.dirname(full_path)

        # 使用 exist_ok=True 来确保目录存在，如果不存在则创建
        os.makedirs(directory, exist_ok=True)

        with open(full_path, 'w') as f:
            json.dump({"session": session_data}, f)
        print(f"Session saved to {full_path}")

    @staticmethod
    def load_session(session, full_path: str):
        """从文件加载会话，如果文件不存在则创建新的会话文件"""
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
            SessionManager.import_session(session, data["session"])
            print(f"Session loaded from {full_path}")
        except FileNotFoundError:
            print(f"Session file not found at {full_path}. Creating a new session file.")
            SessionManager.save_session(session, full_path)

    @staticmethod
    def manage_session(session, file_path: str, filename: str):
        """管理用户会话，自动决定保存或加载，如果文件或目录不存在则创建"""
        full_path = SessionManager.get_full_path(file_path, filename)

        if os.path.exists(full_path):
            SessionManager.load_session(session, full_path)
        else:
            print(f"Session file not found. Creating a new one at {full_path}")
            SessionManager.save_session(session, full_path)

        # 最后检查确保文件已创建
        if not os.path.exists(full_path):
            print(f"Failed to create session file. Retrying...")
            SessionManager.save_session(session, full_path)

        print(f"Session file is now available at {full_path}")