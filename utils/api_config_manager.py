"""
API配置管理器
支持OpenAI、Anthropic等多种大模型API配置
"""
import json
import os
import base64
import sys
from typing import Dict, List, Optional
from datetime import datetime


class APIConfigManager:
    """API配置管理器"""
    
    # 预置的大模型服务商配置
    PRESET_PROVIDERS = {
        "minimax_token_plan": {
            "name": "MiniMax Token Plan",
            "api_type": "minimax_token_plan",
            "base_url": "https://api.minimaxi.com/anthropic/v1",
            "description": "MiniMax Token Plan (Anthropic Compatible)",
            "models": ["MiniMax-M2.7"],
            "default_model": "MiniMax-M2.7"
        },
        "minimax_official": {
            "name": "MiniMax Official",
            "api_type": "minimax_official",
            "base_url": "https://api.minimax.chat/v1",
            "description": "MiniMax官方标准接口",
            "models": ["abab6.5-chat", "abab5.5-chat"],
            "default_model": "abab6.5-chat"
        },
        "openai": {
            "name": "OpenAI",
            "api_type": "openai",
            "base_url": "https://api.openai.com/v1",
            "description": "OpenAI官方API",
            "models": ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"],
            "default_model": "gpt-4"
        },
        "anthropic": {
            "name": "Anthropic",
            "api_type": "anthropic",
            "base_url": "https://api.anthropic.com/v1",
            "description": "Anthropic Claude API",
            "models": ["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"],
            "default_model": "claude-3-opus"
        },
        "qwen": {
            "name": "通义千问",
            "api_type": "openai_compatible",
            "base_url": "https://dashscope.aliyuncs.com/api/v1",
            "description": "阿里云通义千问API",
            "models": ["qwen-max", "qwen-plus", "qwen-turbo"],
            "default_model": "qwen-max"
        },
        "deepseek": {
            "name": "DeepSeek",
            "api_type": "openai_compatible",
            "base_url": "https://api.deepseek.com/v1",
            "description": "DeepSeek API",
            "models": ["deepseek-chat", "deepseek-coder"],
            "default_model": "deepseek-chat"
        },
        "zhipu": {
            "name": "GLM (智谱AI)",
            "api_type": "openai_compatible",
            "base_url": "https://open.bigmodel.cn/api/paas/v4",
            "description": "智谱AI GLM API",
            "models": ["glm-4", "glm-3-turbo"],
            "default_model": "glm-4"
        },
        "doubao": {
            "name": "豆包 (火山方舟)",
            "api_type": "openai_compatible",
            "base_url": "https://ark.cn-beijing.volces.com/api/v3",
            "description": "豆包/火山方舟 OpenAI 兼容接口",
            "models": ["doubao-pro-32k", "doubao-lite-32k"],
            "default_model": "doubao-pro-32k"
        },
        "siliconflow": {
            "name": "硅基流动",
            "api_type": "openai_compatible",
            "base_url": "https://api.siliconflow.cn/v1",
            "description": "SiliconFlow OpenAI 兼容接口",
            "models": ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"],
            "default_model": "Qwen/Qwen2.5-72B-Instruct"
        },
        "feishu": {
            "name": "飞书模型网关",
            "api_type": "openai_compatible",
            "base_url": "",
            "description": "飞书/企业网关（OpenAI兼容，需填写自定义端点）",
            "models": ["custom-model"],
            "default_model": "custom-model"
        }
    }
    
    def __init__(self, config_dir: str = None):
        """初始化配置管理器"""
        if config_dir is None:
            # 默认配置目录：源码模式放项目内；打包模式放用户目录
            if getattr(sys, 'frozen', False):
                appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
                config_dir = os.path.join(appdata, 'RaincourseAIHelper', 'config')
            else:
                from utils.utils import get_project_root
                config_dir = os.path.join(get_project_root(), "config")
        
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, "api_configs.json")
        
        # 确保配置目录存在
        os.makedirs(config_dir, exist_ok=True)
        
        # 加载配置
        self.configs = self._load_configs()

    def _machine_salt(self) -> str:
        """生成与当前机器相关的盐值（轻量混淆，不是强加密）。"""
        return f"{os.name}|{os.environ.get('USERNAME', '')}|RaincourseAPI"

    def _obfuscate_key(self, provider_id: str, api_key: str) -> str:
        if not api_key:
            return ""
        plain = api_key.encode('utf-8')
        salt = (self._machine_salt() + provider_id).encode('utf-8')
        mixed = bytes([b ^ salt[i % len(salt)] for i, b in enumerate(plain)])
        return base64.b64encode(mixed).decode('ascii')

    def _deobfuscate_key(self, provider_id: str, encoded: str) -> str:
        if not encoded:
            return ""
        raw = base64.b64decode(encoded.encode('ascii'))
        salt = (self._machine_salt() + provider_id).encode('utf-8')
        plain = bytes([b ^ salt[i % len(salt)] for i, b in enumerate(raw)])
        return plain.decode('utf-8')

    def _migrate_legacy_configs(self):
        """迁移旧配置格式（明文api_key、旧provider id）。"""
        changed = False

        # 迁移旧 provider id: minimax -> minimax_token_plan
        if self.configs.get("current_provider") == "minimax":
            self.configs["current_provider"] = "minimax_token_plan"
            changed = True

        providers = self.configs.get("providers", {})
        if "minimax" in providers and "minimax_token_plan" not in providers:
            providers["minimax_token_plan"] = providers.pop("minimax")
            changed = True

        # 迁移明文api_key -> api_key_enc
        for provider_id, cfg in providers.items():
            if cfg.get("api_key") and not cfg.get("api_key_enc"):
                cfg["api_key_enc"] = self._obfuscate_key(provider_id, cfg["api_key"])
                cfg.pop("api_key", None)
                changed = True

            # 默认启用状态
            if "enabled" not in cfg:
                cfg["enabled"] = (provider_id == self.configs.get("current_provider"))
                changed = True

        if changed:
            self._save_configs()
    
    def _load_configs(self) -> Dict:
        """加载配置文件"""
        configs = None
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    configs = json.load(f)
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                configs = self._get_default_configs()
        else:
            configs = self._get_default_configs()

        if "providers" not in configs:
            configs["providers"] = {}
        if "current_provider" not in configs:
            configs["current_provider"] = "minimax_token_plan"

        self.configs = configs
        self._migrate_legacy_configs()
        return self.configs
    
    def _get_default_configs(self) -> Dict:
        """获取默认配置"""
        return {
            "current_provider": "minimax_token_plan",
            "providers": {},
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    def _save_configs(self):
        """保存配置文件"""
        try:
            self.configs["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.configs, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def get_preset_providers(self) -> List[Dict]:
        """获取预置的服务商列表"""
        providers = []
        for key, config in self.PRESET_PROVIDERS.items():
            providers.append({
                "id": key,
                **config
            })
        return providers
    
    def get_all_providers(self) -> List[Dict]:
        """获取所有配置的服务商(包括预置和自定义)"""
        providers = self.get_preset_providers()
        current_id = self.configs.get("current_provider")
        
        # 添加自定义配置的服务商
        for provider_id, config in self.configs.get("providers", {}).items():
            if provider_id not in self.PRESET_PROVIDERS:
                providers.append({
                    "id": provider_id,
                    **config
                })

        for provider in providers:
            provider_id = provider["id"]
            saved = self.configs.get("providers", {}).get(provider_id, {})
            key = ""
            try:
                key = self._deobfuscate_key(provider_id, saved.get("api_key_enc", ""))
            except Exception:
                key = ""

            provider["configured"] = bool(key)
            provider["enabled"] = bool(saved.get("enabled", False))
            provider["is_using"] = provider_id == current_id and provider["enabled"]
            provider["api_key_masked"] = (key[:8] + "***" + key[-4:]) if len(key) > 12 else ("***" if key else "")
        
        return providers
    
    def get_provider_config(self, provider_id: str) -> Optional[Dict]:
        """获取指定服务商的配置"""
        # 先检查预置配置
        if provider_id in self.PRESET_PROVIDERS:
            preset = self.PRESET_PROVIDERS[provider_id]
            # 合并用户自定义的API密钥等配置
            user_config = dict(self.configs.get("providers", {}).get(provider_id, {}))
            key = ""
            try:
                key = self._deobfuscate_key(provider_id, user_config.get("api_key_enc", ""))
            except Exception:
                key = ""
            user_config["api_key"] = key
            user_config["configured"] = bool(key)
            user_config["enabled"] = bool(user_config.get("enabled", False))
            return {**preset, **user_config}
        
        # 再检查自定义配置
        if provider_id in self.configs.get("providers", {}):
            custom = dict(self.configs["providers"][provider_id])
            key = ""
            try:
                key = self._deobfuscate_key(provider_id, custom.get("api_key_enc", ""))
            except Exception:
                key = ""
            custom["api_key"] = key
            custom["configured"] = bool(key)
            custom["enabled"] = bool(custom.get("enabled", False))
            return custom
        
        return None
    
    def set_provider_api_key(self, provider_id: str, api_key: str, 
                            base_url: str = None, default_model: str = None):
        """设置服务商的API密钥"""
        if "providers" not in self.configs:
            self.configs["providers"] = {}
        
        if provider_id not in self.configs["providers"]:
            self.configs["providers"][provider_id] = {}
        
        # 空字符串表示不覆盖已有key
        if api_key:
            self.configs["providers"][provider_id]["api_key_enc"] = self._obfuscate_key(provider_id, api_key)
            self.configs["providers"][provider_id].pop("api_key", None)
            self.configs["providers"][provider_id]["enabled"] = True
            self.configs["current_provider"] = provider_id
        
        if base_url:
            self.configs["providers"][provider_id]["base_url"] = base_url
        
        if default_model:
            self.configs["providers"][provider_id]["default_model"] = default_model
        
        return self._save_configs()

    def set_provider_enabled(self, provider_id: str, enabled: bool) -> bool:
        """启用或停用指定服务商。启用时会自动设为当前使用。"""
        if provider_id not in self.PRESET_PROVIDERS and provider_id not in self.configs.get("providers", {}):
            return False

        if "providers" not in self.configs:
            self.configs["providers"] = {}
        if provider_id not in self.configs["providers"]:
            self.configs["providers"][provider_id] = {}

        if enabled:
            # 必须先配置key再允许启用
            try:
                key = self._deobfuscate_key(provider_id, self.configs["providers"][provider_id].get("api_key_enc", ""))
            except Exception:
                key = ""
            if not key:
                return False

        if enabled:
            # 启用一个时，其他都停用，避免“当前使用”歧义
            for pid in self.configs["providers"]:
                self.configs["providers"][pid]["enabled"] = False
            self.configs["providers"][provider_id]["enabled"] = True
            self.configs["current_provider"] = provider_id
        else:
            self.configs["providers"][provider_id]["enabled"] = False
            if self.configs.get("current_provider") == provider_id:
                self.configs["current_provider"] = None

        return self._save_configs()
    
    def set_current_provider(self, provider_id: str) -> bool:
        """设置当前使用的服务商"""
        # 验证服务商是否存在
        if provider_id not in self.PRESET_PROVIDERS and \
           provider_id not in self.configs.get("providers", {}):
            return False

        return self.set_provider_enabled(provider_id, True)
    
    def get_current_provider(self) -> Optional[Dict]:
        """获取当前使用的服务商配置"""
        current_id = self.configs.get("current_provider")
        if current_id:
            cfg = self.get_provider_config(current_id)
            if cfg and cfg.get("enabled", False):
                return cfg
        return None
    
    def add_custom_provider(self, provider_id: str, name: str, api_type: str,
                           base_url: str, api_key: str = None,
                           models: List[str] = None, default_model: str = None,
                           description: str = "") -> bool:
        """添加自定义服务商"""
        if "providers" not in self.configs:
            self.configs["providers"] = {}
        
        self.configs["providers"][provider_id] = {
            "name": name,
            "api_type": api_type,
            "base_url": base_url,
            "description": description,
            "models": models or [],
            "default_model": default_model or (models[0] if models else ""),
            "is_custom": True
        }
        
        if api_key:
            self.configs["providers"][provider_id]["api_key_enc"] = self._obfuscate_key(provider_id, api_key)
            self.configs["providers"][provider_id]["enabled"] = True
            self.configs["current_provider"] = provider_id
        
        return self._save_configs()
    
    def remove_custom_provider(self, provider_id: str) -> bool:
        """删除自定义服务商"""
        if provider_id in self.PRESET_PROVIDERS:
            return False  # 不能删除预置服务商
        
        if provider_id in self.configs.get("providers", {}):
            del self.configs["providers"][provider_id]
            
            # 如果删除的是当前服务商,切换到默认
            if self.configs.get("current_provider") == provider_id:
                self.configs["current_provider"] = "minimax_token_plan"
            
            return self._save_configs()
        
        return False
    
    def test_api_connection(self, provider_id: str) -> Dict:
        """测试API连接"""
        config = self.get_provider_config(provider_id)
        
        if not config:
            return {
                "success": False,
                "message": "服务商配置不存在"
            }
        
        api_key = config.get("api_key")
        if not api_key:
            return {
                "success": False,
                "message": "未配置API密钥"
            }
        
        try:
            # 根据API类型进行测试
            api_type = config.get("api_type")
            base_url = config.get("base_url")
            
            if api_type == "minimax_token_plan":
                # 测试MiniMax Token Plan API (Anthropic Compatible)
                import requests
                headers = {
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": "2023-06-01"
                }
                # 发送一个简单的测试请求
                response = requests.post(
                    f"{base_url}/messages",
                    headers=headers,
                    json={
                        "model": config.get("default_model", "MiniMax-M2.7"),
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "连接成功"}
                else:
                    return {"success": False, "message": f"HTTP {response.status_code}"}

            elif api_type == "minimax_official":
                # 测试MiniMax官方标准接口
                import requests
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": config.get("default_model", "abab6.5-chat"),
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "连接成功"}
                else:
                    return {"success": False, "message": f"HTTP {response.status_code}"}
            
            elif api_type in ["openai", "openai_compatible"]:
                # 测试OpenAI兼容API
                import requests
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                response = requests.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json={
                        "model": config.get("default_model", "gpt-4"),
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "连接成功"}
                else:
                    return {"success": False, "message": f"HTTP {response.status_code}"}
            
            elif api_type == "anthropic":
                # 测试Anthropic API
                import requests
                headers = {
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                }
                response = requests.post(
                    f"{base_url}/messages",
                    headers=headers,
                    json={
                        "model": config.get("default_model", "claude-3-opus"),
                        "messages": [{"role": "user", "content": "test"}],
                        "max_tokens": 10
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    return {"success": True, "message": "连接成功"}
                else:
                    return {"success": False, "message": f"HTTP {response.status_code}"}
            
            else:
                return {
                    "success": False,
                    "message": f"不支持的API类型: {api_type}"
                }
        
        except Exception as e:
            return {
                "success": False,
                "message": f"连接测试失败: {str(e)}"
            }
