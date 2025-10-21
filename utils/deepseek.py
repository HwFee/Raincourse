import requests
import json

class DeepSeekClient:
    """
    用于与 DeepSeek API 交互的客户端。
    """
    def __init__(self, deepseek_api_key: str, model_name: str = "deepseek-chat"):
        """
        初始化 DeepSeek 客户端。

        Args:
            deepseek_api_key (str): 你的 DeepSeek API 密钥。
            model_name (str): 要使用的 DeepSeek 模型名称，例如 "deepseek-chat" 或 "deepseek-coder"。
        """
        self.deepseek_api_key = deepseek_api_key
        self.deepseek_model_name = model_name
        # DeepSeek API 的聊天完成端点
        self.deepseek_api_base_url = "https://api.deepseek.com/v1/chat/completions"

    def get_answer_by_deepseek(self, question: str) -> str:
        """
        使用 DeepSeek API 回答问题，模拟大学生的回答风格，并以纯文本输出。

        Args:
            question (str): 要回答的问题。

        Returns:
            str: DeepSeek 模型生成的纯文本回答，或错误信息。
        """
        # 优化后的提示词，用于指导DeepSeek模型生成大学生风格的纯文本回答
        tip = "你是一个大学生，请用纯文本形式回答以下问题。你的回答应该展现出大学生的思考方式和语言风格，不需要使用任何格式标记（如Markdown）。不要出现除逗号，句号，问号，感叹号，省略号，破折号以外的其他符号"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.deepseek_api_key}"
        }

        payload = {
            "model": self.deepseek_model_name,
            "messages": [
                {"role": "system", "content": tip}, # 使用优化后的提示词作为系统消息
                {"role": "user", "content": question} # 用户的实际问题
            ],
            "stream": False, # 不需要流式响应
            "temperature": 0.7, # 控制回答的创造性，0.7是一个平衡值，既有新意又保持连贯性
            "max_tokens": 1024 # 限制回答的最大长度，避免过长的回复
        }

        try:
            response = requests.post(self.deepseek_api_base_url, headers=headers, json=payload)
            response.raise_for_status() # 对于4xx/5xx的HTTP错误，抛出 requests.exceptions.HTTPError 异常
            response_data = response.json()

            # 检查响应结构，提取回答内容
            if "choices" in response_data and len(response_data["choices"]) > 0:
                answer = response_data["choices"][0]["message"]["content"]
                return answer
            else:
                return "DeepSeek API未能返回有效回答，或响应结构异常。原始响应：" + json.dumps(response_data, ensure_ascii=False)

        except requests.exceptions.RequestException as e:
            # 处理网络连接、请求超时等问题
            return f"DeepSeek API请求失败，请检查网络连接或API配置: {e}"
        except json.JSONDecodeError:
            # 处理API返回非JSON格式响应的情况
            return "DeepSeek API返回的响应不是有效的JSON格式，请检查API服务状态或URL。"
        except Exception as e:
            # 捕获其他未知错误
            return f"发生未知错误: {e}"
