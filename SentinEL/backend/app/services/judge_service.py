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
            
            # Save the audit log
            self._save_audit_log(user_profile.get("user_id", "unknown"), audit_result)
            
            return audit_result

        except Exception as e:
            logger.error(f"Error during AI audit: {e}")
            # Return a fallback/error result so the flow doesn't crash
            return {
                "score": 0,
                "reasoning": f"Audit process failed: {str(e)}",
                "flags": ["SYSTEM_ERROR"]
            }

    def evaluate_email_quality(self, email_content: str, user_risk: str) -> Dict:
        """
        Specialized evaluation for generated emails.
        """
        prompt = f"""
        你是一名严格的企业合规审计员。请检查以下发给 {user_risk} 风险用户的邮件草稿。
        
        邮件内容:
        \"\"\"
        {email_content}
        \"\"\"
        
        请检查:
        1. 是否包含过度承诺 (如 "免费送手机", "保证不收费")?
        2. 语气是否恰当? (高风险用户应更有同理心，低风险用户应更简洁)
        3. 是否包含敏感词或攻击性语言?
        
        输出 JSON:
        {{
            "score": 1-10, 
            "reason": "...",
            "is_safe": bool
        }}
        """
        generation_config = GenerationConfig(
            temperature=0.1,
            response_mime_type="application/json"
        )
        try:
            response = self.model.generate_content(prompt, generation_config=generation_config)
            result = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            return result
        except Exception as e:
            logger.error(f"Email evaluation failed: {e}")
            return {"score": 5, "reason": "Evaluation failed", "is_safe": True}

    def _save_audit_log(self, user_id: str, result: Dict):
        """
        Persist audit log. For now, we mock this by appending to a global list or local file.
        In production, this should go to Firestore or BigQuery.
        """
        # Mock Persistence
        import time
        log_entry = {
            "timestamp": time.time(),
            "user_id": user_id,
            "score": result.get("score"),
            "flags": result.get("flags", []),
            "reasoning": result.get("reasoning") or result.get("reason")
        }
        
        # Simple file-based mock db
        try:
            import os
            LOG_FILE = "audit_logs.jsonl"
            with open(LOG_FILE, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to save audit log: {e}")

    def get_recent_audits(self, limit: int = 10) -> List[Dict]:
        """
        Retrieve recent audit logs.
        """
        audits = []
        try:
            if os.path.exists("audit_logs.jsonl"):
                with open("audit_logs.jsonl", "r") as f:
                    lines = f.readlines()
                    for line in reversed(lines):
                        if len(audits) >= limit:
                            break
                        try:
                            audits.append(json.loads(line))
                        except:
                            continue
        except Exception as e:
            logger.error(f"Failed to read audit logs: {e}")
        
        return audits

