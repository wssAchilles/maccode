"""
LLM Service - 企业级 Gemini 大模型服务

包含 OpenTelemetry 手动埋点，用于 Google Cloud Trace 可视化。
"""

import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
from app.core.telemetry import get_tracer
import os

# 获取 Tracer 实例
tracer = get_tracer()


class LLMService:
    def __init__(self):
        # Configuration
        self.project_id = "sentinel-ai-project-482208"
        self.location = "us-central1"
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Model Configuration
        self.llm_model_name = "gemini-2.5-pro"  # 通用模型 (用于邮件生成等复杂任务)
        self.embedding_model_name = "text-embedding-004"
        
        # ====== 微调模型配置 (Sentinel 专属) ======
        # 训练于: 2025-12-25, 基于 gemini-2.0-flash-001
        # 用途: 简单问答、快速分析 (不支持 system prompt)
        self.tuned_model_id = "projects/672705370432/locations/us-central1/models/5869006152091156608@1"
        self.use_tuned_model = os.getenv("USE_TUNED_MODEL", "true").lower() == "true"
        # ==========================================
        
        # 始终初始化通用模型 (用于复杂的邮件生成任务)
        self.general_model = GenerativeModel(self.llm_model_name)
        print(f"ℹ️ 通用模型已加载: {self.llm_model_name}")
        
        # 初始化微调模型 (用于简单任务)
        if self.use_tuned_model:
            try:
                self.tuned_model = GenerativeModel(self.tuned_model_id)
                self.active_model_name = "sentinel-tuned-gemini"
                print(f"✅ 已加载 Sentinel 微调模型: {self.tuned_model_id}")
            except Exception as e:
                print(f"⚠️ 微调模型加载失败: {e}")
                self.tuned_model = None
                self.active_model_name = self.llm_model_name
        else:
            self.tuned_model = None
            self.active_model_name = self.llm_model_name
            print(f"ℹ️ 微调模型已禁用")
        
        # 保持向后兼容 - generative_model 指向通用模型
        self.generative_model = self.general_model
        
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)

    def get_text_embedding(self, text: str) -> list[float]:
        """
        生成文本的向量嵌入。
        
        Trace Span: "Vertex AI: Text Embedding"
        """
        # 创建追踪 Span
        with tracer.start_as_current_span("Vertex AI: Text Embedding") as span:
            span.set_attribute("ai.model", self.embedding_model_name)
            span.set_attribute("ai.provider", "vertex_ai")
            span.set_attribute("input.text_length", len(text))
            
            try:
                embeddings = self.embedding_model.get_embeddings([text])
                result = embeddings[0].values
                
                # 记录结果到 Span
                span.set_attribute("output.dimensions", len(result))
                
                return result
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"Error generating embedding: {e}")
                raise e

    def generate_retention_email(self, user_profile: dict, policies: list[str]) -> str:
        """
        使用 Gemini 生成个性化挽留邮件。
        
        Trace Span: "Gemini: Generate Email"
        """
        # 创建追踪 Span
        with tracer.start_as_current_span("Gemini: Generate Email") as span:
            span.set_attribute("ai.model", self.llm_model_name)
            span.set_attribute("ai.provider", "vertex_ai")
            span.set_attribute("input.policies_count", len(policies))
            
            feature_context = user_profile.get("features", {})
            user_id = user_profile.get("user_id", "Unknown")
            churn_prob = user_profile.get("churn_probability", 0.0)
            
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.churn_probability", churn_prob)
            
            system_prompt = """
            你是一个高级客户关系专家 (SentinEL)。你的目标是根据数据和公司政策挽留高价值客户。
            严禁编造优惠政策，必须基于工具检索到的信息。
            语气要诚恳、专业且具有个性化。
            """
            
            policies_text = "\n".join([f"- {p}" for p in policies])
            
            user_prompt = f"""
            客户画像:
            - ID: {user_id}
            - 国家: {feature_context.get('country', 'Unknown')}
            - 来源: {feature_context.get('traffic_source', 'Unknown')}
            - 过去90天消费: {feature_context.get('monetary_90d', 0)}
            - 风险概率: {churn_prob:.2f}

            检索到的公司挽留政策:
            {policies_text}

            任务:
            请为该客户起草一封挽留邮件。
            1. 针对其具体情况（如高消费、地区等）进行个性化问候。
            2. 巧妙地提供上述政策中适用的权益。
            3. 保持简短有力。
            """
            
            generation_config = {
                "temperature": 0.7,
                "max_output_tokens": 500,
            }
            
            try:
                response = self.generative_model.generate_content(
                    [system_prompt, user_prompt],
                    generation_config=generation_config
                )
                result = response.text
                
                # 记录结果到 Span
                span.set_attribute("output.text_length", len(result))
                
                return result
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"Error generating email: {e}")
                return "Unable to generate email at this time."

