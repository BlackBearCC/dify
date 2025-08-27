"""
完整版豆包问答机器人 - 可独立运行

使用方法：
1. 确保已安装 requests 库: pip install requests
2. 直接运行此文件: python doubao_chatbot.py
3. 或者在Python环境中导入使用

API配置已内置，无需额外配置
"""

import requests
import json
import re
import sys
from typing import Dict, Any, Optional, List

class DoubaoConfig:
    """豆包API配置"""
    API_KEY = "b633a622-b5d0-4f16-a8a9-616239cf15d1"
    BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 可用模型端点
    MODELS = {
        "doubao-1.6": "ep-20250612123019-mb9bb",           # 最强模型
        "doubao-1.6-thinking": "ep-20250612123438-7fj94",   # 思考模型
        "doubao-1.6-flash": "ep-20250612122042-t6g56",      # 快速模型
        "doubao-1.5-pro-32k": "ep-20250312153153-npj4s",    # Pro模型
        "doubao-1.5-lite-32k": "ep-20250312153312-hwtd2",   # 轻量模型
        "doubao-1.5-pro-256k": "ep-20250312153332-jfhkj",   # 长文本模型
        "kimi-v1-32k": "ep-20250522163423-s49tn",           # Kimi模型
    }

class DoubaoClient:
    """豆包API客户端"""
    
    def __init__(self):
        self.config = DoubaoConfig()
        self.headers = {
            "Authorization": f"Bearer {self.config.API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "DoubaoQABot/1.0"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             model: str = "doubao-1.6-flash",
             temperature: float = 0.7,
             max_tokens: int = 1000,
             timeout: int = 30) -> Optional[str]:
        """发送聊天请求"""
        
        endpoint_id = self.config.MODELS.get(model)
        if not endpoint_id:
            print(f"❌ 未知模型: {model}")
            return None
        
        url = f"{self.config.BASE_URL}/chat/completions"
        payload = {
            "model": endpoint_id,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            print(f"🚀 调用模型: {model} ({endpoint_id})")
            
            response = self.session.post(url, json=payload, timeout=timeout)
            
            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                
                # 计算token使用情况（如果API返回）
                usage = result.get("usage", {})
                if usage:
                    print(f"📊 Token使用: 输入{usage.get('prompt_tokens', 0)} + 输出{usage.get('completion_tokens', 0)} = 总计{usage.get('total_tokens', 0)}")
                
                return content
            else:
                print(f"❌ API调用失败: {response.status_code}")
                print(f"错误详情: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            print("❌ 请求超时，请稍后重试")
            return None
        except requests.exceptions.RequestException as e:
            print(f"❌ 网络请求失败: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ 未知错误: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """测试API连接"""
        print("🧪 测试豆包API连接...")
        
        test_messages = [{"role": "user", "content": "你好，请说'连接成功'"}]
        result = self.chat(test_messages, model="doubao-1.6-flash", max_tokens=50)
        
        if result:
            print(f"✅ 连接测试成功: {result}")
            return True
        else:
            print("❌ 连接测试失败")
            return False

class QuestionAnalyzer:
    """问题分析器"""
    
    def __init__(self, client: DoubaoClient):
        self.client = client
    
    def analyze(self, question: str) -> Dict[str, Any]:
        """分析问题"""
        
        analyze_prompt = f"""请分析以下用户问题，只返回JSON格式结果：

问题：{question}

JSON格式：
{{
    "category": "事实性问题|意见咨询|技术问题|日常对话|创意写作|其他",
    "complexity": "简单|中等|复杂",
    "topic": "问题的主要话题",
    "language": "中文|英文|其他",
    "requires_research": true/false,
    "estimated_tokens": 数字
}}

只返回JSON，不要任何解释。"""

        messages = [{"role": "user", "content": analyze_prompt}]
        result = self.client.chat(messages, model="doubao-1.6-flash", temperature=0.2, max_tokens=200)
        
        if result:
            try:
                # 提取JSON
                json_match = re.search(r'\{.*\}', result, re.DOTALL)
                if json_match:
                    analysis = json.loads(json_match.group())
                    print(f"📊 问题分析: {analysis['category']} | {analysis['complexity']} | {analysis['topic']}")
                    return analysis
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ 分析结果解析失败: {e}")
        
        # 默认分析
        default = {
            "category": "其他",
            "complexity": "中等",
            "topic": "一般问题",
            "language": "中文",
            "requires_research": False,
            "estimated_tokens": 300
        }
        print(f"📊 使用默认分析: {default}")
        return default

class AnswerGenerator:
    """回答生成器"""
    
    def __init__(self, client: DoubaoClient):
        self.client = client
        
        # 对话风格定义
        self.styles = {
            "友好": {
                "description": "用温暖、亲切的语言，像朋友一样交流",
                "tone": "亲切、温暖、支持性"
            },
            "专业": {
                "description": "用严谨、准确的术语，保持专业性和权威性",
                "tone": "严谨、准确、专业"
            },
            "幽默": {
                "description": "在准确回答的同时，适当加入幽默和趣味元素",
                "tone": "轻松、有趣、幽默"
            },
            "简洁": {
                "description": "用最少的文字准确回答，去除冗余信息",
                "tone": "简洁、直接、高效"
            },
            "学术": {
                "description": "用学术化的语言，提供深入的分析和引用",
                "tone": "学术、深入、严谨"
            }
        }
    
    def select_model(self, analysis: Dict[str, Any]) -> str:
        """根据问题分析选择合适的模型"""
        
        complexity = analysis.get("complexity", "中等")
        category = analysis.get("category", "其他")
        
        # 复杂问题或需要深度思考的问题使用最强模型
        if complexity == "复杂" or category in ["技术问题", "创意写作"]:
            return "doubao-1.6"
        # 需要快速响应的简单问题使用快速模型
        elif complexity == "简单" or category == "日常对话":
            return "doubao-1.6-flash"
        # 其他情况使用平衡模型
        else:
            return "doubao-1.6"
    
    def generate(self, question: str, analysis: Dict[str, Any], style: str = "友好") -> str:
        """生成回答"""
        
        # 选择模型
        model = self.select_model(analysis)
        
        # 获取风格配置
        style_config = self.styles.get(style, self.styles["友好"])
        
        # 构建提示词
        if analysis["complexity"] == "复杂":
            prompt = self._build_complex_prompt(question, analysis, style_config)
            max_tokens = 1200
        else:
            prompt = self._build_simple_prompt(question, analysis, style_config)
            max_tokens = 600
        
        messages = [{"role": "user", "content": prompt}]
        
        print(f"💭 使用{model}生成{style}风格的回答...")
        result = self.client.chat(messages, model=model, temperature=0.7, max_tokens=max_tokens)
        
        return result if result else "抱歉，我现在无法回答这个问题。请稍后再试，或者换个方式提问。"
    
    def _build_complex_prompt(self, question: str, analysis: Dict[str, Any], style_config: Dict[str, str]) -> str:
        """构建复杂问题的提示词"""
        
        return f"""你是一个知识渊博、经验丰富的AI助手，擅长回答各种复杂问题。

【用户问题】
{question}

【问题分析】
- 类别: {analysis["category"]}
- 复杂度: {analysis["complexity"]}
- 主题: {analysis["topic"]}

【回答要求】
1. 风格: {style_config["tone"]} - {style_config["description"]}
2. 如果是事实性问题，提供准确信息和相关背景
3. 如果是技术问题，给出详细解决步骤和原理解释
4. 如果是意见咨询，提供平衡观点和实用建议
5. 如果是创意问题，发挥想象力但保持逻辑性
6. 结构清晰，层次分明，适当使用例子和类比
7. 承认不确定的信息，不编造事实

请提供一个全面、准确、有价值的回答。"""
    
    def _build_simple_prompt(self, question: str, analysis: Dict[str, Any], style_config: Dict[str, str]) -> str:
        """构建简单问题的提示词"""
        
        return f"""你是一个友好、有用的AI助手。

问题: {question}
类别: {analysis["category"]}
风格: {style_config["tone"]} - {style_config["description"]}

要求:
- 回答准确有用
- 语言{style_config["tone"]}
- 简洁明了，直击重点
- 不确定时诚实说明

请直接回答问题。"""

class AnswerOptimizer:
    """回答优化器"""
    
    def __init__(self, client: DoubaoClient):
        self.client = client
    
    def optimize(self, question: str, raw_answer: str, style: str = "友好") -> str:
        """优化回答"""
        
        optimize_prompt = f"""请优化以下AI回答，使其更完善：

【原始回答】
{raw_answer}

【原问题】
{question}

【风格要求】
{style}

【优化要求】
1. 保持核心内容和观点不变
2. 改善语言表达，使其更自然流畅
3. 适当调整结构，提高可读性
4. 在结尾添加一句关怀性的话，询问是否还有其他问题
5. 确保符合{style}的风格特点
6. 如果回答过长，保持原有逻辑结构

直接输出优化后的回答，不要添加说明文字。"""

        messages = [{"role": "user", "content": optimize_prompt}]
        
        result = self.client.chat(messages, model="doubao-1.6-flash", temperature=0.5, max_tokens=1000)
        
        return result if result else raw_answer

class DoubaoQABot:
    """豆包问答机器人主类"""
    
    def __init__(self):
        self.client = DoubaoClient()
        self.analyzer = QuestionAnalyzer(self.client)
        self.generator = AnswerGenerator(self.client)
        self.optimizer = AnswerOptimizer(self.client)
        
        # 统计信息
        self.stats = {
            "questions_answered": 0,
            "total_tokens_used": 0,
            "avg_response_time": 0
        }
    
    def answer(self, question: str, style: str = "友好", optimize: bool = True) -> Dict[str, Any]:
        """回答问题的完整流程"""
        
        import time
        start_time = time.time()
        
        print(f"\n🤖 开始处理问题: {question}")
        print(f"🎨 对话风格: {style}")
        print("=" * 50)
        
        try:
            # 1. 问题分析
            print("📊 步骤1: 分析问题...")
            analysis = self.analyzer.analyze(question)
            
            # 2. 生成回答
            print("💭 步骤2: 生成回答...")
            raw_answer = self.generator.generate(question, analysis, style)
            
            # 3. 优化回答（可选）
            if optimize and raw_answer:
                print("✨ 步骤3: 优化回答...")
                final_answer = self.optimizer.optimize(question, raw_answer, style)
            else:
                final_answer = raw_answer
            
            # 4. 计算处理时间
            process_time = time.time() - start_time
            
            # 5. 更新统计
            self.stats["questions_answered"] += 1
            self.stats["avg_response_time"] = (
                (self.stats["avg_response_time"] * (self.stats["questions_answered"] - 1) + process_time) 
                / self.stats["questions_answered"]
            )
            
            # 6. 构建结果
            result = {
                "question": question,
                "style": style,
                "analysis": analysis,
                "raw_answer": raw_answer,
                "final_answer": final_answer,
                "model_used": self.generator.select_model(analysis),
                "process_time": round(process_time, 2),
                "optimized": optimize,
                "success": True
            }
            
            print(f"✅ 处理完成! 耗时 {process_time:.2f}秒")
            return result
            
        except Exception as e:
            print(f"❌ 处理失败: {str(e)}")
            return {
                "question": question,
                "error": str(e),
                "success": False
            }
    
    def batch_answer(self, questions: List[str], style: str = "友好") -> List[Dict[str, Any]]:
        """批量回答问题"""
        
        print(f"📝 开始批量处理 {len(questions)} 个问题...")
        results = []
        
        for i, question in enumerate(questions, 1):
            print(f"\n{'='*20} 问题 {i}/{len(questions)} {'='*20}")
            result = self.answer(question, style)
            results.append(result)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.stats.copy()
    
    def test_all_models(self, test_question: str = "你好，请介绍一下自己。") -> Dict[str, str]:
        """测试所有可用模型"""
        
        print(f"🧪 测试所有模型，测试问题: {test_question}")
        results = {}
        
        for model_name in self.client.config.MODELS.keys():
            print(f"\n测试模型: {model_name}")
            
            messages = [{"role": "user", "content": test_question}]
            response = self.client.chat(messages, model=model_name, max_tokens=100)
            
            results[model_name] = response if response else "调用失败"
        
        return results

def run_interactive_mode():
    """交互模式"""
    
    print("🤖 豆包问答机器人 v1.0")
    print("=" * 50)
    print("💡 输入 'quit' 退出")
    print("💡 输入 'help' 查看帮助")
    print("💡 输入 'stats' 查看统计信息")
    print("💡 格式: 问题内容 | 风格 (如: 什么是AI? | 专业)")
    print("=" * 50)
    
    bot = DoubaoQABot()
    
    # 测试连接
    if not bot.client.test_connection():
        print("❌ API连接失败，请检查网络和配置")
        return
    
    available_styles = list(bot.generator.styles.keys())
    
    while True:
        try:
            user_input = input("\n❓ 请输入问题: ").strip()
            
            if not user_input:
                continue
            elif user_input.lower() == 'quit':
                print("👋 感谢使用，再见！")
                break
            elif user_input.lower() == 'help':
                print(f"🎨 可用风格: {', '.join(available_styles)}")
                print("📖 使用方法: 直接输入问题，或用 | 指定风格")
                print("📊 输入 'stats' 查看使用统计")
                continue
            elif user_input.lower() == 'stats':
                stats = bot.get_stats()
                print("📊 使用统计:")
                for key, value in stats.items():
                    print(f"   {key}: {value}")
                continue
            
            # 解析输入
            if '|' in user_input:
                parts = user_input.split('|', 1)
                question = parts[0].strip()
                style = parts[1].strip()
                if style not in available_styles:
                    print(f"⚠️ 未知风格 '{style}'，使用默认风格 '友好'")
                    style = "友好"
            else:
                question = user_input
                style = "友好"
            
            # 回答问题
            result = bot.answer(question, style)
            
            if result["success"]:
                print(f"\n🤖 回答 ({result['analysis']['category']} | {result['model_used']}):")
                print(result["final_answer"])
                print(f"\n⏱️ 处理时间: {result['process_time']}秒")
            else:
                print(f"❌ 回答失败: {result.get('error', '未知错误')}")
            
        except KeyboardInterrupt:
            print("\n👋 感谢使用，再见！")
            break
        except Exception as e:
            print(f"❌ 程序错误: {str(e)}")

def run_test_suite():
    """运行测试套件"""
    
    print("🧪 豆包问答机器人测试套件")
    print("=" * 50)
    
    bot = DoubaoQABot()
    
    # 测试API连接
    if not bot.client.test_connection():
        print("❌ 测试失败：API连接不可用")
        return
    
    # 测试问题集
    test_questions = [
        ("什么是人工智能？", "专业"),
        ("今天心情不好怎么办？", "友好"),
        ("Python装饰器怎么用？", "简洁"),
        ("为什么猫咪喜欢纸箱？", "幽默"),
        ("量子计算的基本原理", "学术")
    ]
    
    print(f"\n📝 开始测试 {len(test_questions)} 个问题...")
    
    all_results = []
    for question, style in test_questions:
        result = bot.answer(question, style)
        all_results.append(result)
        
        if result["success"]:
            print(f"\n✅ 成功: {question[:20]}...")
        else:
            print(f"\n❌ 失败: {question[:20]}...")
    
    # 显示统计
    stats = bot.get_stats()
    success_count = sum(1 for r in all_results if r["success"])
    
    print(f"\n📊 测试结果:")
    print(f"   总问题数: {len(test_questions)}")
    print(f"   成功回答: {success_count}")
    print(f"   成功率: {success_count/len(test_questions)*100:.1f}%")
    print(f"   平均响应时间: {stats['avg_response_time']:.2f}秒")
    
    return all_results

def main():
    """主函数"""
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        if mode == "test":
            run_test_suite()
        elif mode == "interactive":
            run_interactive_mode()
        else:
            print("可用模式: test | interactive")
    else:
        # 默认运行测试套件
        run_test_suite()

if __name__ == "__main__":
    main()