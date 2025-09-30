"""
模型配置解析工具
从环境变量中解析AI模型配置信息
"""

import os
from typing import List, Dict, Any
from app.models.ai import AIModel
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ModelConfigParser:
    """模型配置解析器"""
    
    @staticmethod
    def parse_list_from_env(env_var: str, default_list: List[str] = None) -> List[str]:
        """从环境变量解析逗号分隔的列表"""
        value = os.getenv(env_var, '')
        if not value.strip():
            return default_list or []
        return [item.strip() for item in value.split(',') if item.strip()]
    
    @staticmethod
    def parse_openai_models() -> List[AIModel]:
        """解析OpenAI模型配置"""
        try:
            models = ModelConfigParser.parse_list_from_env('OPENAI_MODELS')
            names = ModelConfigParser.parse_list_from_env('OPENAI_MODEL_NAMES')
            descriptions = ModelConfigParser.parse_list_from_env('OPENAI_MODEL_DESCRIPTIONS')
            max_tokens_str = ModelConfigParser.parse_list_from_env('OPENAI_MODEL_MAX_TOKENS')
            
            # 确保所有列表长度一致
            if not models:
                return []
            
            # 补齐缺失的配置信息
            while len(names) < len(models):
                names.append(f"OpenAI Model {len(names) + 1}")
            while len(descriptions) < len(models):
                descriptions.append("OpenAI模型")
            while len(max_tokens_str) < len(models):
                max_tokens_str.append("8192")
            
            # 转换为整数
            try:
                max_tokens = [int(token) for token in max_tokens_str]
            except ValueError as e:
                logger.warning(f"解析OpenAI max_tokens失败: {e}, 使用默认值")
                max_tokens = [8192] * len(models)
            
            # 创建AIModel对象
            ai_models = []
            for i, model_id in enumerate(models):
                ai_model = AIModel(
                    value=model_id,
                    label=names[i] if i < len(names) else model_id,
                    description=descriptions[i] if i < len(descriptions) else "OpenAI模型",
                    features=ModelConfigParser._get_openai_features(model_id),
                    max_tokens=max_tokens[i] if i < len(max_tokens) else 8192
                )
                ai_models.append(ai_model)
                
            logger.info(f"成功解析 {len(ai_models)} 个OpenAI模型")
            return ai_models
            
        except Exception as e:
            logger.error(f"解析OpenAI模型配置失败: {str(e)}")
            # 返回默认模型配置
            return ModelConfigParser._get_default_openai_models()
    
    @staticmethod
    def parse_claude_models() -> List[AIModel]:
        """解析Claude模型配置"""
        try:
            models = ModelConfigParser.parse_list_from_env('CLAUDE_MODELS')
            names = ModelConfigParser.parse_list_from_env('CLAUDE_MODEL_NAMES')
            descriptions = ModelConfigParser.parse_list_from_env('CLAUDE_MODEL_DESCRIPTIONS')
            max_tokens_str = ModelConfigParser.parse_list_from_env('CLAUDE_MODEL_MAX_TOKENS')
            
            # 确保所有列表长度一致
            if not models:
                return []
                
            # 补齐缺失的配置信息
            while len(names) < len(models):
                names.append(f"Claude Model {len(names) + 1}")
            while len(descriptions) < len(models):
                descriptions.append("Claude模型")
            while len(max_tokens_str) < len(models):
                max_tokens_str.append("200000")
            
            # 转换为整数
            try:
                max_tokens = [int(token) for token in max_tokens_str]
            except ValueError as e:
                logger.warning(f"解析Claude max_tokens失败: {e}, 使用默认值")
                max_tokens = [200000] * len(models)
            
            # 创建AIModel对象
            ai_models = []
            for i, model_id in enumerate(models):
                ai_model = AIModel(
                    value=model_id,
                    label=names[i] if i < len(names) else model_id,
                    description=descriptions[i] if i < len(descriptions) else "Claude模型",
                    features=ModelConfigParser._get_claude_features(model_id),
                    max_tokens=max_tokens[i] if i < len(max_tokens) else 200000
                )
                ai_models.append(ai_model)
                
            logger.info(f"成功解析 {len(ai_models)} 个Claude模型")
            return ai_models
            
        except Exception as e:
            logger.error(f"解析Claude模型配置失败: {str(e)}")
            # 返回默认模型配置
            return ModelConfigParser._get_default_claude_models()

    @staticmethod
    def parse_deepseek_models() -> List[AIModel]:
        """解析Deepseek模型配置"""
        try:
            models = ModelConfigParser.parse_list_from_env('DEEPSEEK_MODELS')
            names = ModelConfigParser.parse_list_from_env('DEEPSEEK_MODEL_NAMES')
            descriptions = ModelConfigParser.parse_list_from_env('DEEPSEEK_MODEL_DESCRIPTIONS')
            max_tokens_str = ModelConfigParser.parse_list_from_env('DEEPSEEK_MODEL_MAX_TOKENS')

            # 确保所有列表长度一致
            if not models:
                return []

            # 补齐缺失的配置信息
            while len(names) < len(models):
                names.append(f"Deepseek Model {len(names) + 1}")
            while len(descriptions) < len(models):
                descriptions.append("Deepseek模型")
            while len(max_tokens_str) < len(models):
                max_tokens_str.append("128000")

            # 转换为整数
            try:
                max_tokens = [int(token) for token in max_tokens_str]
            except ValueError as e:
                logger.warning(f"解析Deepseek max_tokens失败: {e}, 使用默认值")
                max_tokens = [128000] * len(models)

            # 创建AIModel对象
            ai_models = []
            for i, model_id in enumerate(models):
                ai_model = AIModel(
                    value=model_id,
                    label=names[i] if i < len(names) else model_id,
                    description=descriptions[i] if i < len(descriptions) else "Deepseek模型",
                    features=ModelConfigParser._get_deepseek_features(model_id),
                    max_tokens=max_tokens[i] if i < len(max_tokens) else 128000
                )
                ai_models.append(ai_model)

            logger.info(f"成功解析 {len(ai_models)} 个Deepseek模型")
            return ai_models

        except Exception as e:
            logger.error(f"解析Deepseek模型配置失败: {str(e)}")
            # 返回默认模型配置
            return ModelConfigParser._get_default_deepseek_models()

    @staticmethod
    def _get_deepseek_features(model_id: str) -> List[str]:
        """根据模型ID获取Deepseek模型特性"""
        if 'reasoner' in model_id:
            return ["深度推理", "逻辑分析", "问题求解", "数学计算", "代码生成"]
        else:
            return ["对话交互", "文本生成", "推理分析", "网络诊断"]
    
    @staticmethod
    def _get_openai_features(model_id: str) -> List[str]:
        """根据模型ID获取OpenAI模型特性"""
        if 'gpt-5' in model_id:
            return ["最智能AI", "内置思维链", "专家级智能", "多模态", "推理分析", "代码生成"]
        elif 'gpt-4.1' in model_id:
            return ["超大上下文", "指令优化", "代码生成", "推理分析", "长文档处理"]
        elif model_id.startswith('o3') or model_id.startswith('o4'):
            return ["深度推理", "数学专家", "编程专家", "科学计算", "逻辑推理"]
        elif 'gpt-4o' in model_id:
            return ["多模态", "文本生成", "代码生成", "图像理解", "推理分析"]
        elif 'gpt-4' in model_id:
            return ["文本生成", "代码生成", "推理分析", "复杂问题求解"]
        elif 'gpt-3.5' in model_id:
            return ["文本生成", "对话交互", "快速响应"]
        else:
            return ["文本生成", "对话交互"]
    
    @staticmethod
    def _get_claude_features(model_id: str) -> List[str]:
        """根据模型ID获取Claude模型特性"""
        if 'opus-4' in model_id:
            return ["世界级编程", "持续性能", "长时间任务", "复杂推理", "代码生成"]
        elif 'sonnet-4' in model_id:
            return ["编程专家", "超大上下文", "成本优化", "推理分析", "代码生成"]
        elif '3-7-sonnet' in model_id:
            return ["混合推理", "双模式响应", "深度思考", "快速响应", "灵活切换"]
        elif 'opus' in model_id:
            return ["复杂推理", "代码生成", "创意写作", "深度分析"]
        elif 'sonnet' in model_id:
            if '3-5' in model_id:
                return ["平衡性能", "代码生成", "分析推理", "最新功能", "计算机操作"]
            else:
                return ["平衡性能", "文本生成", "代码生成", "分析推理"]
        elif 'haiku' in model_id:
            if '3-5' in model_id:
                return ["高性能", "快速响应", "轻量级", "文本生成", "成本优化"]
            else:
                return ["快速响应", "轻量级", "文本生成"]
        else:
            return ["文本生成", "分析推理"]
    
    @staticmethod
    def _get_default_openai_models() -> List[AIModel]:
        """获取默认的OpenAI模型配置"""
        return [
            AIModel(
                value="gpt-4",
                label="GPT-4",
                description="最新的GPT-4模型，具有强大的推理能力",
                features=["文本生成", "代码生成", "推理分析"],
                max_tokens=8192
            ),
            AIModel(
                value="gpt-3.5-turbo",
                label="GPT-3.5 Turbo",
                description="快速且经济的GPT-3.5模型",
                features=["文本生成", "对话交互"],
                max_tokens=4096
            )
        ]
    
    @staticmethod
    def _get_default_claude_models() -> List[AIModel]:
        """获取默认的Claude模型配置"""
        return [
            AIModel(
                value="claude-3-sonnet-20240229",
                label="Claude 3 Sonnet",
                description="平衡性能和速度的Claude 3模型",
                features=["文本生成", "代码生成", "分析推理"],
                max_tokens=200000
            ),
            AIModel(
                value="claude-3-haiku-20240307",
                label="Claude 3 Haiku",
                description="快速且轻量的Claude 3模型",
                features=["快速响应", "文本生成"],
                max_tokens=200000
            )
        ]

    @staticmethod
    def _get_default_deepseek_models() -> List[AIModel]:
        """获取默认的Deepseek模型配置"""
        return [
            AIModel(
                value="deepseek-chat",
                label="DeepSeek-V3.1-Terminus",
                description="深度对话模型",
                features=["对话交互", "文本生成", "推理分析", "网络诊断"],
                max_tokens=128000
            ),
            AIModel(
                value="deepseek-reasoner",
                label="DeepSeek-V3.1-Terminus-Think",
                description="深度推理模型",
                features=["深度推理", "逻辑分析", "问题求解", "数学计算", "代码生成"],
                max_tokens=128000
            )
        ]

    @staticmethod
    def get_all_configured_models() -> Dict[str, List[AIModel]]:
        """获取所有配置的模型"""
        return {
            'openai': ModelConfigParser.parse_openai_models(),
            'claude': ModelConfigParser.parse_claude_models(),
            'deepseek': ModelConfigParser.parse_deepseek_models()
        }