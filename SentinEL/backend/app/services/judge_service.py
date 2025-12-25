import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import json
import logging
from typing import Dict, List, Optional
import os

# 配置日志
logger = logging.getLogger(__name__)

class AIJudge:
    def __init__(self, project_id: str = "sentinel-ai-project-482208", location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        # Initialize Vertex AI
        try:
           vertexai.init(project=project_id, location=location)
           self.model = GenerativeModel("gemini-2.5-pro") # Using 1.5 Pro for better reasoning
           logger.info(f"AIJudge initialized with project {project_id} and model gemini-2.5-pro")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI for AIJudge: {e}")
            raise

    def evaluate_response(self, user_profile: Dict, generated_email: str, applied_policies: List[str]) -> Dict:
        """
        Evaluates the generated email against strict criteria using Gemini.
        """
        
        prompt = f"""
        你是一名严苛的企业合规审计员 (AI Judge)。请根据以下标准对生成的客户挽留邮件进行评分 (0-100) 和点评。

        ### 输入信息
        1. **用户画像**: {json.dumps(user_profile, ensure_ascii=False)}
        2. **应用策略**: {json.dumps(applied_policies, ensure_ascii=False)}
        3. **生成邮件内容**:
        \"\"\"
        {generated_email}
        \"\"\"

        ### 评分标准
        1. **共情度 (Empathy)**: 是否真诚理解客户痛点？行文是否温暖？
        2. **合规性 (Compliance)**: 提供的优惠是否完全符合策略库中的规定？(严禁幻觉/私自承诺，严禁提供策略列表以外的优惠)
        3. **逻辑性 (Logic)**: 邮件内容是否与用户画像矛盾？(例如给仅浏览用户发送“感谢购买”是不合逻辑的)

        ### 输出要求
        请只输出纯 JSON 格式，不要包含 Markdown 标记 (```json ... ```)。字段如下：
        - `score` (int): 0-100 分。
        - `reasoning` (str): 简短犀利的点评 (中文)，指出扣分点或做得好的地方。
        - `flags` (list[str]): 发现的严重问题标签，如 ["HALLUCINATION", "LOGIC_ERROR"]，如果没有则为空列表。
        """

        generation_config = GenerationConfig(
            temperature=0.2, # Low temperature for more deterministic evaluation
            top_p=0.95,
            response_mime_type="application/json"
        )

        try:
            logger.info("Sending audit request to Gemini...")
            response = self.model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            response_text = response.text.strip()
            # Remove markdown code blocks if present, just in case
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            audit_result = json.loads(response_text)
            logger.info(f"Audit complete. Score: {audit_result.get('score')}")
            return audit_result

        except Exception as e:
            logger.error(f"Error during AI audit: {e}")
            # Return a fallback/error result so the flow doesn't crash
            return {
                "score": 0,
                "reasoning": f"Audit process failed: {str(e)}",
                "flags": ["SYSTEM_ERROR"]
            }
