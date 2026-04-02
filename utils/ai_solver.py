"""
AI答题模块 - 多服务商统一调用
"""

import re
import time
import json
import logging
import requests
from typing import Optional, Tuple
from datetime import datetime
import os

# 配置日志
def setup_logger():
    """设置日志记录器"""
    # 确保logs目录存在
    os.makedirs("logs", exist_ok=True)

    # 创建日志记录器
    logger = logging.getLogger('ai_solver')
    logger.setLevel(logging.DEBUG)

    # 避免重复添加handler
    if not logger.handlers:
        # 文件处理器
        log_filename = f"logs/ai_solver_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)

        # 格式化器
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

    return logger

# 全局日志记录器
logger = setup_logger()


class AISolver:
    """多服务商统一答题调用器"""

    def __init__(self, console, api_key: str, api_type: str = "minimax_token_plan", base_url: str = None,
                 model: str = None):
        self.console = console
        self.api_key = api_key
        self.api_type = api_type or "minimax_token_plan"
        if self.api_type == "minimax_official":
            self.base_url = base_url or "https://api.minimax.chat/v1"
            self.model = model or "abab6.5-chat"
        elif self.api_type in ["openai", "openai_compatible"]:
            self.base_url = base_url or "https://api.openai.com/v1"
            self.model = model or "gpt-4"
        elif self.api_type == "anthropic":
            self.base_url = base_url or "https://api.anthropic.com/v1"
            self.model = model or "claude-3-sonnet"
        else:
            self.base_url = base_url or "https://api.minimaxi.com/anthropic/v1"
            self.model = model or "MiniMax-M2.7"

    def _clean_text(self, text: str) -> str:
        """清理文本中的HTML标签和多余空白"""
        text = re.sub(r'<[^>]+>', '', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def call_model(self, question: str, options: list = None, question_type: str = "单选题") -> Optional[str]:
        """调用模型接口（支持多服务商）。"""
        try:
            if self.api_type == "minimax_official":
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                mode = "openai_like"
            elif self.api_type in ["openai", "openai_compatible"]:
                url = f"{self.base_url}/chat/completions"
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                }
                mode = "openai_like"
            elif self.api_type == "anthropic":
                url = f"{self.base_url}/messages"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                }
                mode = "anthropic_like"
            else:
                url = f"{self.base_url}/messages"
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "anthropic-dangerous-direct-browser-access": "true"
                }
                mode = "anthropic_like"

            # 构建提示词
            prompt = f"题目：{question}\n\n"

            if options:
                prompt += "选项：\n"
                for i, opt in enumerate(options):
                    prompt += f"{chr(65+i)}. {opt}\n"
                prompt += "\n"

            prompt += f"""请分析题目并给出答案。

要求：
1. 先用中文简要分析题目
2. 最后用括号输出答案字母

答案格式：
- 单选题：（A）
- 多选题：（A/B/C）或（A、B、C）

请确保答案在选项范围内。"""

            # 记录到日志文件
            logger.info(f"\n{'='*60}")
            logger.info(f"AI接收到的完整内容：")
            logger.info(f"{'='*60}")
            logger.info(f"题目：{question}")
            if options:
                logger.info(f"选项：")
                for i, opt in enumerate(options):
                    logger.info(f"  {chr(65+i)}. {opt}")
            else:
                logger.warning(f"未提取到选项")
            logger.info(f"题型：{question_type}")
            logger.info(f"{'='*60}\n")

            if mode == "openai_like":
                payload = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 2048,
                    "temperature": 0.3,
                }
            else:
                payload = {
                    "model": self.model,
                    "max_tokens": 2048,  # 增加token限制，支持更详细的分析
                    "temperature": 0.3,  # 提高温度，增加灵活性
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }

            self.console.log(f"[cyan]📡 正在调用模型API...[/cyan]")

            response = requests.post(url, headers=headers, json=payload, timeout=60)
            response.encoding = 'utf-8'

            if response.status_code == 200:
                result = response.json()

                # 兼容两种返回格式
                full_response = ""
                if mode == "openai_like":
                    choices = result.get('choices', [])
                    if choices:
                        full_response = ((choices[0].get('message') or {}).get('content') or '')
                else:
                    for item in result.get('content', []):
                        if item.get('type') == 'text':
                            full_response = item.get('text', '')
                            break

                if not full_response:
                    self.console.log(f"[red]❌ API返回为空[/red]")
                    return None

                # 转义Rich特殊字符
                safe_response = full_response.replace('[', '【').replace(']', '】')
                self.console.log(f"[blue]📝 回答: {safe_response}[/blue]")
                return full_response
            else:
                self.console.log(f"[red]❌ 模型API错误: {response.status_code}[/red]")
                self.console.log(f"[red]响应内容: {response.text}[/red]")
                return None

        except Exception as e:
            self.console.log(f"[red]❌ 模型调用失败: {e}[/red]")
            return None

    def extract_options(self, question_body: str, question_dict: dict = None) -> list:
        """从题目中提取选项"""
        options = []

        # 先尝试从题目字典的其他字段提取选项
        if question_dict:
            # 检查是否有 Options 字段
            if 'Options' in question_dict:
                logger.debug(f"检测到 Options 字段")
                logger.debug(f"Options 字段原始内容：{question_dict['Options']}")

                # 尝试提取选项
                opts_data = question_dict['Options']
                if isinstance(opts_data, list):
                    for i, opt in enumerate(opts_data):
                        logger.debug(f"选项 {i}: {opt} (类型: {type(opt).__name__})")
                        if isinstance(opt, dict):
                            # 支持多种字段名：value, Content, OptionText, Text
                            content = opt.get('value', opt.get('Content', opt.get('OptionText', opt.get('Text', ''))))
                            if content:
                                # 清理HTML标签
                                content = self._clean_text(str(content))
                                options.append(content)
                        elif isinstance(opt, str):
                            if opt.strip():
                                # 清理HTML标签
                                content = self._clean_text(opt.strip())
                                options.append(content)
                elif isinstance(opts_data, str):
                    # 如果 Options 是字符串，尝试解析
                    logger.warning(f"Options 是字符串类型，尝试解析")
                    # 可能是 "A.xxx B.xxx C.xxx D.xxx" 格式
                    parts = re.split(r'\s+[A-D][.、）]', opts_data)
                    for part in parts:
                        if part.strip():
                            options.append(part.strip())

                if options:
                    logger.info(f"成功从 Options 字段提取 {len(options)} 个选项")
                    return options[:4]
                else:
                    logger.error(f"Options 字段存在但提取失败")

            # 检查是否有 OptionList 字段
            if 'OptionList' in question_dict:
                logger.debug(f"检测到 OptionList 字段")
                logger.debug(f"OptionList 字段原始内容：{question_dict['OptionList']}")

                for opt in question_dict['OptionList']:
                    if isinstance(opt, dict):
                        content = opt.get('value', opt.get('Content', opt.get('OptionText', opt.get('Text', ''))))
                        if content:
                            content = self._clean_text(str(content))
                            options.append(content)
                    elif isinstance(opt, str):
                        if opt.strip():
                            content = self._clean_text(opt.strip())
                            options.append(content)
                if options:
                    logger.info(f"成功从 OptionList 字段提取 {len(options)} 个选项")
                    return options[:4]

            # 检查是否有 Answer 字段（有些题目选项在答案字段中）
            if 'Answer' in question_dict and isinstance(question_dict['Answer'], dict):
                answer_dict = question_dict['Answer']
                if 'Options' in answer_dict:
                    logger.debug(f"检测到 Answer.Options 字段")
                    logger.debug(f"Answer.Options 字段原始内容：{answer_dict['Options']}")

                    for opt in answer_dict['Options']:
                        if isinstance(opt, dict):
                            content = opt.get('value', opt.get('Content', opt.get('OptionText', opt.get('Text', ''))))
                            if content:
                                content = self._clean_text(str(content))
                                options.append(content)
                    if options:
                        logger.info(f"成功从 Answer.Options 字段提取 {len(options)} 个选项")
                        return options[:4]

        # 如果从其他字段提取失败，再从 Body 中提取
        logger.warning(f"从其他字段提取失败，尝试从 Body 中提取")

        # 先清理题干中的干扰文字（如"假设正确选项为X"）
        cleaned_body = re.sub(r'假设正确选项为[A-D][，。]?', '', question_body)
        cleaned_body = re.sub(r'正确答案[是为：:\s]*[A-D][，。]?', '', cleaned_body)

        logger.debug(f"清理后的题目文本（前200字）：{cleaned_body[:200]}")

        # 修复正则表达式：移除重复的.
        pattern = r'([A-D])[.、）]\s*([^\n]+?)(?=\n[A-D]|\Z)'
        matches = re.findall(pattern, cleaned_body, re.DOTALL)

        if matches:
            logger.debug(f"正则匹配到 {len(matches)} 个选项")
            for letter, content in matches:
                content = content.strip()
                if content:
                    options.append(content)
                    logger.debug(f"选项 {letter}: {content[:50]}...")
        else:
            # 备选方案：直接查找 A. B. C. D. 开头的行
            logger.debug(f"使用备选方案提取选项")
            lines = cleaned_body.split('\n')
            for line in lines:
                line = line.strip()
                if re.match(r'^[A-D][.、）]', line):
                    option_text = re.sub(r'^[A-D][.、）]\s*', '', line)
                    if option_text:
                        options.append(option_text)
                        logger.debug(f"备选方案提取到选项：{option_text[:50]}...")

        # 修复逻辑：只返回前4个选项
        result = options[:4]
        logger.info(f"最终提取到 {len(result)} 个选项")
        return result

    def solve_question(self, question: dict, max_retries: int = 3, stop_event=None) -> Optional[str]:
        """
        使用当前配置模型答题，支持重试机制
        返回最终答案
        """
        question_type = question.get('TypeText', '单选题')  # 从题目数据中获取真实题型
        question_id = question.get('ProblemID', '')
        body = self._clean_text(question.get('Body', ''))

        self.console.log(f"[yellow]正在解答题目 {question_id}...[/yellow]")

        # 记录题目数据结构到日志
        logger.info(f"\n{'='*60}")
        logger.info(f"题目ID: {question_id}")
        logger.info(f"题型: {question_type}")
        logger.debug(f"题目完整数据结构：")
        for key, value in question.items():
            if key == 'Body':
                logger.debug(f"  {key}: (内容过长，已省略)")
            else:
                logger.debug(f"  {key}: {value}")

        options = self.extract_options(body, question)

        # 重试机制
        for attempt in range(1, max_retries + 1):
            # 检查停止信号
            if stop_event and stop_event.is_set():
                self.console.log("[yellow]⏹️ 已收到停止请求，取消当前题目解答[/yellow]")
                return None
            
            try:
                self.console.log(f"[cyan]尝试第 {attempt}/{max_retries} 次...[/cyan]")

                ai_response = self.call_model(body, options, question_type)

                if not ai_response:
                    self.console.log(f"[red]❌ 模型调用失败，准备重试...[/red]")
                    logger.error(f"模型调用失败，尝试 {attempt}/{max_retries}")
                    if attempt < max_retries:
                        time.sleep(2)  # 等待2秒后重试
                    continue

                # 从回答中提取答案
                answer = self.extract_answer_option(ai_response)

                if answer:
                    self.console.log(f"[green]✅ 最终答案: {answer}[/green]")
                    logger.info(f"最终答案: {answer}")
                    return answer
                else:
                    self.console.log(f"[red]❌ 无法从回答中提取答案，准备重试...[/red]")
                    logger.error(f"无法从回答中提取答案，尝试 {attempt}/{max_retries}")
                    if attempt < max_retries:
                        time.sleep(2)
                    continue

            except Exception as e:
                self.console.log(f"[red]答题失败 (尝试 {attempt}/{max_retries}): {e}[/red]")
                logger.error(f"答题失败 (尝试 {attempt}/{max_retries}): {e}")
                if attempt < max_retries:
                    time.sleep(2)
                continue

        self.console.log(f"[bold red]❌ 经过 {max_retries} 次尝试后仍无法解答此题[/bold red]")
        logger.error(f"经过 {max_retries} 次尝试后仍无法解答此题")
        return None

    def extract_answer_option(self, ai_response: Optional[str]) -> Optional[str]:
        """
        从AI的回答中提取括号里的答案（A/B/C/D）
        支持单选题和多选题
        """
        if not ai_response:
            return None

        import re

        # 优先匹配括号内的答案（支持多种分隔符）
        # 匹配格式：（A）、（A/B/C）、（A、B、C）、(A)、(A/B/C)等
        pattern1 = r'[（(]\s*([A-D](?:[/、,，]\s*[A-D])*)\s*[）)]'
        match1 = re.search(pattern1, ai_response, re.IGNORECASE)

        if match1:
            # 提取所有字母并去重
            answer_str = match1.group(1).upper()
            letters = re.findall(r'[A-D]', answer_str)
            unique_letters = sorted(set(letters))

            if unique_letters:
                answer = ''.join(unique_letters)
                self.console.log(f"[green]✅ 提取到答案: {answer}[/green]")
                return answer

        # 备选方案：查找独立的答案字母（避免误匹配）
        # 只在"答案是"、"选择"等关键词附近查找
        pattern2 = r'(?:答案|选择|正确选项)[是为：:\s]*([A-D](?:[/、,，]\s*[A-D])*)'
        match2 = re.search(pattern2, ai_response, re.IGNORECASE)

        if match2:
            answer_str = match2.group(1).upper()
            letters = re.findall(r'[A-D]', answer_str)
            unique_letters = sorted(set(letters))

            if unique_letters:
                answer = ''.join(unique_letters)
                self.console.log(f"[yellow]⚠️ 从关键词提取到答案: {answer}[/yellow]")
                return answer

        self.console.log(f"[red]❌ 无法提取答案[/red]")
        return None
