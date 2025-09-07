# -*- coding: utf-8 -*-
"""
Prompt管理器
负责加载和管理所有分析师的prompt模板
"""

from pathlib import Path
from typing import Dict, Optional


class PromptManager:
    """Prompt模板管理器"""
    
    def __init__(self):
        """初始化Prompt管理器"""
        self.prompts_dir = Path(__file__).parent.parent / "prompts"
        self._prompt_cache: Dict[str, str] = {}
    
    def load_prompt(self, prompt_name: str) -> str:
        """
        加载prompt模板
        
        Args:
            prompt_name: prompt文件名（不含扩展名）
            
        Returns:
            str: prompt内容
        """
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]
        
        prompt_file = self.prompts_dir / f"{prompt_name}.txt"
        
        if not prompt_file.exists():
            print(f"⚠️ Prompt文件不存在: {prompt_file}")
            return self._get_default_prompt(prompt_name)
        
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                self._prompt_cache[prompt_name] = content
                return content
        except Exception as e:
            print(f"❌ 加载prompt失败 {prompt_name}: {e}")
            return self._get_default_prompt(prompt_name)
    
    def _get_default_prompt(self, prompt_name: str) -> str:
        """获取默认prompt模板"""
        default_prompts = {
            'technical_analysis': """你是专业的技术分析师，请分析{symbol}的技术指标：

{context}

请提供：
1. 趋势分析
2. 支撑阻力位
3. 技术指标解读
4. 交易建议

请保持简洁专业的分析。""",
            
            'market_sentiment': """你是市场情绪分析师，请分析当前市场情绪：

{context}

请分析：
1. 当前市场情绪状态
2. 资金流向分析
3. 市场热点趋势
4. 短期情绪预期

请提供客观的市场情绪评估。""",
            
            'fundamental_analysis': """你是基本面分析专家，请分析：

{context}

请分析：
1. 价格走势的基本面逻辑
2. 交易量变化的意义
3. 市值排名变化趋势
4. 长期投资价值评估

保持理性客观的分析视角。""",
            
            'chief_analysis': """你是{symbol}首席分析师，请整合多个分析师的报告：

{context}

{analyst_reports}

请提供：
1. 各维度分析的一致性和分歧点
2. 短期和中长期投资策略
3. 风险因素的多维度评估
4. 关键市场转折点和信号

请提供具体、可操作的{symbol}投资建议。"""
        }
        
        return default_prompts.get(prompt_name, "你是专业的分析师，请提供分析报告。")
    
    def get_technical_analysis_prompt(self) -> str:
        """获取技术分析prompt"""
        return self.load_prompt('technical_analysis')
    
    def get_market_sentiment_prompt(self) -> str:
        """获取市场情绪分析prompt"""
        return self.load_prompt('market_sentiment')
    
    def get_fundamental_analysis_prompt(self) -> str:
        """获取基本面分析prompt"""
        return self.load_prompt('fundamental_analysis')
    
    def get_chief_analysis_prompt(self) -> str:
        """获取首席分析师prompt"""
        return self.load_prompt('chief_analysis')
    
    def get_macro_analysis_prompt(self) -> str:
        """获取宏观分析prompt"""
        return self.load_prompt('macro_analysis')
    
    def get_coin_chief_analysis_prompt(self) -> str:
        """获取币种首席分析师prompt（兼容性方法）"""
        return self.get_chief_analysis_prompt()
    
    def reload_prompts(self):
        """重新加载所有prompt"""
        self._prompt_cache.clear()
        print("🔄 Prompt缓存已清理，将重新加载")