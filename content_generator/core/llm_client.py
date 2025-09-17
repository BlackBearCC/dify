# -*- coding: utf-8 -*-
"""
LLM客户端 - 支持Claude和豆包模型的统一接口
支持模型：
- Claude系列 (Anthropic)
- 豆包系列 (字节跳动)
- Kimi系列 (月之暗面)
- DeepSeek系列 (DeepSeek)
"""

import requests
import json
import time
import sys
import re
from typing import Optional, Dict, Any, List
from enum import Enum

class LLMProvider(Enum):
    """LLM提供商枚举"""
    CLAUDE = "claude"
    DOUBAO = "doubao"
    DEEPSEEK = "deepseek"

class LLMClient:
    """统一的LLM客户端，支持多个模型提供商"""

    @staticmethod
    def _remove_think_tags(text: str) -> str:
        """移除文本中的<think>和</think>标签及其内容"""
        # 移除<think>...</think>标签及其内容
        pattern = r'<think>.*?</think>'
        cleaned_text = re.sub(pattern, '', text, flags=re.DOTALL)
        # 清理多余的空行
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', cleaned_text)
        return cleaned_text.strip()

    # 豆包平台模型映射
    DOUBAO_MODELS = {
        # 豆包模型
        "doubao-1.5-pro-32k": "ep-20250312153153-npj4s",
        "doubao-1.5-lite-32k": "ep-20250312153312-hwtd2", 
        "doubao-1.5-pro-256k": "ep-20250312153332-jfhkj",
        "doubao-1.5-pro-character": "ep-20250312153655-ntg8z",
        "doubao-1.5-thinking-pro": "ep-20250417214536-hpndh",
        "doubao-1.6": "ep-20250612123019-mb9bb",
        "doubao-1.6-thinking": "ep-20250612123438-7fj94",
        "doubao-1.6-flash": "ep-20250612122042-t6g56",
        "doubao-embedding": "ep-20250312154514-xrm58",

        # 豆包视觉模型映射
        "doubao-vision-pro": "ep-20250704095927-j6t2g",
        

        
        # DeepSeek模型
        "deepseek-V3": "ep-20250221154410-vh78x",
        "deepseek-R1": "ep-20250221154107-c4qc7"
    }
    
    def __init__(self, 
                 provider: LLMProvider = LLMProvider.CLAUDE,
                 model: str = "claude-sonnet-4-20250514",
                 api_key: str = None,
                 base_url: str = None):
        """
        初始化LLM客户端
        
        Args:
            provider: LLM提供商 (CLAUDE, DOUBAO, KIMI, DEEPSEEK)
            model: 模型名称
            api_key: API密钥
            base_url: 基础URL
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        
        # 设置默认配置
        self._setup_default_config()
        
        print(f"🤖 LLM客户端初始化: {self.provider.value} - {self.model}")
        
    def _setup_default_config(self):
        """设置默认配置"""
        if self.provider == LLMProvider.CLAUDE:
            if not self.base_url:
                self.base_url = "https://club.claudecode.site"
            self.endpoint = f"{self.base_url}/v1/messages"
            
        elif self.provider in [LLMProvider.DOUBAO, LLMProvider.DEEPSEEK]:
            if not self.base_url:
                self.base_url = "https://ark.cn-beijing.volces.com/api/v3"
            self.endpoint = f"{self.base_url}/chat/completions"
            
            # 将友好名称转换为endpoint ID
            if self.model in self.DOUBAO_MODELS:
                self.endpoint_id = self.DOUBAO_MODELS[self.model]
                print(f"📋 模型映射: {self.model} -> {self.endpoint_id}")
            else:
                self.endpoint_id = self.model  # 如果直接提供endpoint ID
    
    def call(self, system_prompt_or_full_prompt: str,
             user_message: Optional[str] = None,
             agent_name: str = "Assistant",
             max_tokens: int = 2000,
             temperature: float = 0.7,
             stream: bool = True,
             enable_thinking: bool = False) -> str:
        """
        调用LLM API的统一接口 - 支持分离的系统提示和用户消息

        Args:
            system_prompt_or_full_prompt: 系统提示词，如果user_message为None，则作为完整提示
            user_message: 用户消息（可选），如果提供则与system_prompt分离
            agent_name: 代理名称（用于日志）
            max_tokens: 最大token数
            temperature: 温度参数
            stream: 是否流式输出
            enable_thinking: 是否启用thinking模式（仅适用于doubao模型）

        Returns:
            str: LLM响应内容
        """
        if not self.api_key:
            error_msg = f"❌ [{agent_name}] 未配置{self.provider.value} API密钥"
            print(error_msg, flush=True)
            return error_msg
        
        print(f"🤖 [{agent_name}] 调用{self.provider.value}模型: {self.model}", flush=True)
        
        try:
            # 计算提示长度用于日志
            if user_message is not None:
                total_length = len(system_prompt_or_full_prompt) + len(user_message)
                print(f"📝 提示长度: {total_length} 字符 (系统提示: {len(system_prompt_or_full_prompt)}, 用户消息: {len(user_message)})", flush=True)
            else:
                print(f"📝 提示长度: {len(system_prompt_or_full_prompt)} 字符", flush=True)
            
            if self.provider == LLMProvider.CLAUDE:
                response = self._call_claude_api(system_prompt_or_full_prompt, user_message, agent_name, max_tokens, stream)
            else:
                response = self._call_doubao_api(system_prompt_or_full_prompt, user_message, agent_name, max_tokens, temperature, stream, enable_thinking)
            
            print(f"✅ [{agent_name}] 响应完成，共{len(response)}字符", flush=True)

            # 如果是doubao模型且禁用了thinking模式，清理可能残留的think标签
            if (self.provider == LLMProvider.DOUBAO and
                hasattr(self, '_thinking_disabled') and self._thinking_disabled):
                response = self._remove_think_tags(response)

            return response
                
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ [{agent_name}] {self.provider.value}调用失败: {e}\n详细错误:\n{error_detail}"
            print(error_msg, flush=True)
            return error_msg
    
    def _call_claude_api(self, system_prompt_or_full_prompt: str, user_message: Optional[str], 
                         agent_name: str, max_tokens: int, stream: bool) -> str:
        """调用Claude API - 支持分离的系统提示和用户消息"""
        if user_message is not None:
            # 分离模式：系统提示 + 用户消息
            payload = {
                "model": self.model,
                "system": system_prompt_or_full_prompt,
                "messages": [{"role": "user", "content": user_message}],
                "max_tokens": max_tokens,
                "stream": stream
            }
        else:
            # 兼容模式：单个完整提示
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": system_prompt_or_full_prompt}],
                "max_tokens": max_tokens,
                "stream": stream
            }
        
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        
        return self._make_request(payload, headers, agent_name, stream)
    
    def _call_doubao_api(self, system_prompt_or_full_prompt: str, user_message: Optional[str],
                         agent_name: str, max_tokens: int, temperature: float, stream: bool, enable_thinking: bool = False) -> str:
        """调用豆包/Kimi/DeepSeek API - 支持分离的系统提示和用户消息"""
        if user_message is not None:
            # 分离模式：系统提示 + 用户消息
            messages = [
                {"role": "system", "content": system_prompt_or_full_prompt},
                {"role": "user", "content": user_message}
            ]
        else:
            # 兼容模式：单个完整提示
            messages = [{"role": "user", "content": system_prompt_or_full_prompt}]

        payload = {
            "model": self.endpoint_id,  # 使用endpoint ID
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream
        }

        # 添加thinking模式控制（仅对doubao模型有效）
        if self.provider == LLMProvider.DOUBAO:
            thinking_type = "enabled" if enable_thinking else "disabled"
            payload["extra"] = {
                "thinking": {"type": thinking_type}
            }
            # 设置标志，用于后续清理think标签
            self._thinking_disabled = not enable_thinking
            if not enable_thinking:
                print(f"🧠 [{agent_name}] Thinking模式已禁用，将去除<think>标签", flush=True)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        return self._make_request(payload, headers, agent_name, stream)
    
    def call_with_image(self, system_prompt: str, user_message: str,
                       image_base64: str, image_mime: str = "image/jpeg",
                       agent_name: str = "Assistant",
                       max_tokens: int = 4096,
                       temperature: float = 0.7) -> str:
        """
        调用支持图片的LLM API

        Args:
            system_prompt: 系统提示词
            user_message: 用户消息
            image_base64: Base64编码的图片数据
            image_mime: 图片MIME类型
            agent_name: 代理名称
            max_tokens: 最大token数
            temperature: 温度参数

        Returns:
            str: LLM响应内容
        """
        if not self.api_key:
            error_msg = f"❌ [{agent_name}] 未配置{self.provider.value} API密钥"
            print(error_msg, flush=True)
            return error_msg

        if self.provider != LLMProvider.DOUBAO:
            error_msg = f"❌ [{agent_name}] 当前仅支持豆包模型的图片识别功能"
            print(error_msg, flush=True)
            return error_msg

        print(f"🖼️ [{agent_name}] 调用豆包视觉模型: {self.model}", flush=True)

        try:
            return self._call_doubao_vision_api(system_prompt, user_message, image_base64,
                                              image_mime, agent_name, max_tokens, temperature)
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ [{agent_name}] 豆包视觉模型调用失败: {e}\n详细错误:\n{error_detail}"
            print(error_msg, flush=True)
            return error_msg

    def _call_doubao_vision_api(self, system_prompt: str, user_message: str,
                               image_base64: str, image_mime: str,
                               agent_name: str, max_tokens: int, temperature: float) -> str:
        """调用豆包视觉API"""
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_message},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{image_mime};base64,{image_base64}"
                        }
                    }
                ]
            }
        ]

        payload = {
            "model": self.endpoint_id,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False  # 图片识别暂不支持流式
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        return self._make_request(payload, headers, agent_name, False)

    def _make_request(self, payload: dict, headers: dict, agent_name: str, stream: bool) -> str:
        """发送HTTP请求"""
        try:
            response = requests.post(self.endpoint, json=payload, headers=headers, timeout=60, stream=stream)

            if response.status_code != 200:
                error_msg = f"❌ [{agent_name}] API请求失败: {response.status_code} - {response.text}"
                print(error_msg, flush=True)
                return error_msg

            if stream:
                return self._handle_stream_response(response, agent_name)
            else:
                return self._handle_normal_response(response, agent_name)

        except requests.exceptions.Timeout:
            error_msg = f"❌ [{agent_name}] 请求超时"
            print(error_msg, flush=True)
            return error_msg
        except requests.exceptions.RequestException as e:
            error_msg = f"❌ [{agent_name}] 网络请求错误: {e}"
            print(error_msg, flush=True)
            return error_msg
    
    def _handle_stream_response(self, response, agent_name: str) -> str:
        """处理流式响应"""
        full_response = ""
        buffer = ""
        
        try:
            for chunk in response:
                if chunk:
                    buffer += chunk.decode('utf-8', errors='ignore')
                    
                    # 处理完整的行
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('data: '):
                            data_text = line[6:]
                            if data_text.strip() == '[DONE]':
                                break
                            
                            try:
                                data = json.loads(data_text)
                                
                                # Claude格式
                                if self.provider == LLMProvider.CLAUDE:
                                    if data.get('type') == 'content_block_delta':
                                        if 'delta' in data and data['delta'].get('type') == 'text_delta':
                                            chunk_text = data['delta']['text']
                                            print(chunk_text, end='', flush=True)
                                            sys.stdout.flush()
                                            full_response += chunk_text
                                
                                # 豆包/Kimi/DeepSeek格式
                                else:
                                    if 'choices' in data and len(data['choices']) > 0:
                                        choice = data['choices'][0]
                                        if 'delta' in choice and 'content' in choice['delta']:
                                            chunk_text = choice['delta']['content']
                                            if chunk_text:
                                                print(chunk_text, end='', flush=True)
                                                sys.stdout.flush()
                                                full_response += chunk_text
                                                
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"⚠️ [{agent_name}] 处理数据错误: {e}", flush=True)
                                continue
            
            print()  # 换行
            
            if not full_response.strip():
                error_msg = f"❌ [{agent_name}] 未收到有效响应内容"
                print(error_msg, flush=True)
                return error_msg
            
            return full_response.strip()
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ [{agent_name}] 流式响应处理错误: {e}\n详细错误:\n{error_detail}"
            print(error_msg, flush=True)
            return error_msg
    
    def _handle_normal_response(self, response, agent_name: str) -> str:
        """处理普通响应"""
        try:
            data = response.json()
            
            # Claude格式
            if self.provider == LLMProvider.CLAUDE:
                if 'content' in data and len(data['content']) > 0:
                    return data['content'][0]['text']
            
            # 豆包/Kimi/DeepSeek格式
            else:
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0]['message']['content']
            
            error_msg = f"❌ [{agent_name}] 响应格式异常: {data}"
            print(error_msg, flush=True)
            return error_msg
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            error_msg = f"❌ [{agent_name}] 响应解析错误: {e}\n详细错误:\n{error_detail}"
            print(error_msg, flush=True)
            return error_msg

# 便捷的工厂函数
def create_claude_client(api_key: str, model: str = "claude-sonnet-4-20250514", base_url: str = None) -> LLMClient:
    """创建Claude客户端"""
    return LLMClient(
        provider=LLMProvider.CLAUDE,
        model=model,
        api_key=api_key,
        base_url=base_url
    )

def create_doubao_client(api_key: str, model: str = "doubao-1.6", base_url: str = None) -> LLMClient:
    """创建豆包客户端"""
    return LLMClient(
        provider=LLMProvider.DOUBAO,
        model=model,
        api_key=api_key,
        base_url=base_url
    )

def create_deepseek_client(api_key: str, model: str = "deepseek-V3", base_url: str = None) -> LLMClient:
    """创建DeepSeek客户端"""
    return LLMClient(
        provider=LLMProvider.DEEPSEEK,
        model=model,
        api_key=api_key,
        base_url=base_url
    )