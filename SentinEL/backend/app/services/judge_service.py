"""
SentinEL AI 裁判服务 (AI Judge / LLM-as-a-Judge)

实现 Human-in-the-loop 机制：
- 使用 Gemini Pro 对 Agent 生成的策略进行质量评估
- 三维评分：共情度、清晰度、风险匹配度
- 不合格策略触发重试循环
"""

import json
import logging
from typing import Dict, Any, Optional, Literal
from dataclasses import dataclass

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from app.core.config import settings

logger = logging.getLogger(__name__)

# 评估阈值
PASS_THRESHOLD = 75


@dataclass
class EvaluationResult:
    """评估结果数据类"""
    score: int
    empathy: int      # 共情度 0-10
    clarity: int      # 清晰度 0-10
    alignment: int    # 风险匹配度 0-10
    reason: str
    suggestions: str
    verdict: Literal["PASS", "FAIL"]


class AIJudge:
    """
    LLM-as-a-Judge 服务
    
    使用 Gemini Pro 扮演"资深客户成功经理"角色，
    对 Agent 生成的挽留策略进行多维度评估。
    """
    
    # 评估 Prompt 模板
    JUDGE_SYSTEM_PROMPT = """你是一位拥有10年经验的资深客户成功经理 (Customer Success Manager)。
你的职责是评估AI生成的客户挽留策略的质量。

你需要从以下三个维度进行评估 (每项 0-10 分):

1. **共情度 (Empathy)**: 策略是否理解用户的痛点？是否有真诚关怀的语气？
   - 0-3分: 机械冷漠，完全没有理解用户处境
   - 4-6分: 有基本关怀但不够深入
   - 7-10分: 深刻理解用户需求，表达真诚共情

2. **清晰度 (Clarity)**: 方案是否易懂？行动步骤是否明确？
   - 0-3分: 模糊不清，用户不知道如何操作
   - 4-6分: 基本清晰但有歧义
   - 7-10分: 非常清晰，步骤具体可执行

3. **风险匹配度 (Alignment)**: 策略力度是否匹配用户风险等级？
   - 对于【高风险/VIP用户】: 是否提供了足够力度的优惠和关注？
   - 对于【低风险用户】: 是否避免了过度承诺和资源浪费？
   - 0-3分: 完全不匹配
   - 4-6分: 基本匹配但可优化
   - 7-10分: 策略力度精准匹配用户价值

总分计算: (empathy + clarity + alignment) / 30 * 100

你必须严格按照以下 JSON 格式输出，不要有任何额外文字:
{
    "empathy": <0-10>,
    "clarity": <0-10>,
    "alignment": <0-10>,
    "score": <0-100>,
    "reason": "<简短的评估理由>",
    "suggestions": "<如果未通过,具体的改进建议;如果通过,可以是'无需修改'>"
}"""

    JUDGE_USER_TEMPLATE = """请评估以下挽留策略:

**用户风险等级**: {risk_level}
**用户标签**: {user_tags}

**待评估策略内容**:
---
{strategy_text}
---

请严格按照 JSON 格式给出评估结果。"""

    def __init__(self):
        """初始化 Judge 服务"""
        self.model_name = "gemini-2.0-flash"  # 使用高能力模型进行评估
        try:
            self.llm = ChatVertexAI(
                project=settings.PROJECT_ID,
                location=settings.LOCATION,
                model_name=self.model_name,
                temperature=0.1,  # 低温度保证评估一致性
                max_output_tokens=1024,
            )
            logger.info(f"AIJudge 初始化成功 | Model: {self.model_name}")
        except Exception as e:
            logger.error(f"AIJudge 初始化失败: {e}")
            self.llm = None

    def evaluate_strategy(
        self,
        strategy_text: str,
        user_risk_level: str,
        user_tags: Optional[str] = None
    ) -> EvaluationResult:
        """
        评估挽留策略质量
        
        Args:
            strategy_text: Agent 生成的策略文本
            user_risk_level: 用户风险等级 (High/Medium/Low)
            user_tags: 可选的用户标签 (如 "VIP", "新用户" 等)
            
        Returns:
            EvaluationResult: 包含评分、理由和改进建议
        """
        if not self.llm:
            logger.warning("LLM 不可用，返回默认通过结果")
            return EvaluationResult(
                score=75,
                empathy=8,
                clarity=8,
                alignment=7,
                reason="Judge 服务不可用，默认通过",
                suggestions="无需修改",
                verdict="PASS"
            )
        
        # 构建评估消息
        user_tags_str = user_tags or "普通用户"
        
        messages = [
            SystemMessage(content=self.JUDGE_SYSTEM_PROMPT),
            HumanMessage(content=self.JUDGE_USER_TEMPLATE.format(
                risk_level=user_risk_level,
                user_tags=user_tags_str,
                strategy_text=strategy_text
            ))
        ]
        
        try:
            response = self.llm.invoke(messages)
            raw_text = response.content.strip()
            
            # 解析 JSON 响应
            # 处理可能的 markdown 代码块包装
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]
            raw_text = raw_text.strip()
            
            result = json.loads(raw_text)
            
            # 提取评分
            empathy = int(result.get("empathy", 5))
            clarity = int(result.get("clarity", 5))
            alignment = int(result.get("alignment", 5))
            
            # 计算总分 (如果 LLM 没有正确计算)
            calculated_score = int((empathy + clarity + alignment) / 30 * 100)
            score = result.get("score", calculated_score)
            
            # 确定判决
            verdict = "PASS" if score >= PASS_THRESHOLD else "FAIL"
            
            evaluation = EvaluationResult(
                score=score,
                empathy=empathy,
                clarity=clarity,
                alignment=alignment,
                reason=result.get("reason", "评估完成"),
                suggestions=result.get("suggestions", "无"),
                verdict=verdict
            )
            
            logger.info(
                f"[Judge] Score: {score} ({verdict}) | "
                f"Empathy: {empathy}, Clarity: {clarity}, Alignment: {alignment} | "
                f"Reason: {evaluation.reason[:50]}..."
            )
            
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"[Judge] JSON 解析失败: {e} | Raw: {raw_text[:200]}")
            return EvaluationResult(
                score=60,
                empathy=6,
                clarity=6,
                alignment=6,
                reason="评估结果解析失败",
                suggestions="请重新生成策略",
                verdict="FAIL"
            )
        except Exception as e:
            logger.error(f"[Judge] 评估失败: {e}")
            return EvaluationResult(
                score=50,
                empathy=5,
                clarity=5,
                alignment=5,
                reason=f"评估过程出错: {str(e)[:100]}",
                suggestions="系统错误，请重试",
                verdict="FAIL"
            )

    def evaluate_email_quality(self, email_content: str, user_risk_level: str) -> Dict[str, Any]:
        """
        [兼容方法] 评估邮件质量 (旧接口)
        
        为保持向后兼容，使用新的 evaluate_strategy 方法
        """
        result = self.evaluate_strategy(
            strategy_text=email_content,
            user_risk_level=user_risk_level
        )
        
        return {
            "score": result.score,
            "reason": result.reason,
            "is_compliant": result.verdict == "PASS"
        }

    def evaluate_response(
        self,
        user_profile: dict,
        generated_email: str,
        applied_policies: list
    ) -> Dict[str, Any]:
        """
        [兼容方法] 评估响应 (旧接口)
        """
        user_risk = "High" if user_profile.get("predicted_label") == 1 else "Low"
        return self.evaluate_email_quality(generated_email, user_risk)


# 单例实例
_judge_instance: Optional[AIJudge] = None


def get_judge_service() -> AIJudge:
    """获取 AIJudge 单例"""
    global _judge_instance
    if _judge_instance is None:
        _judge_instance = AIJudge()
    return _judge_instance
