import vertexai
from vertexai.generative_models import GenerativeModel
from vertexai.language_models import TextEmbeddingModel
import os

class LLMService:
    def __init__(self):
        # Configuration
        self.project_id = "sentinel-ai-project-482208"
        self.location = "us-central1"
        
        # Initialize Vertex AI
        vertexai.init(project=self.project_id, location=self.location)
        
        # Model Configuration
        # Using the requested top-tier model
        self.llm_model_name = "gemini-1.5-pro-002"
        self.embedding_model_name = "text-embedding-004"
        
        self.generative_model = GenerativeModel(self.llm_model_name)
        self.embedding_model = TextEmbeddingModel.from_pretrained(self.embedding_model_name)

    def get_text_embedding(self, text: str) -> list[float]:
        """
        Generates embedding vector for a given text.
        """
        try:
            embeddings = self.embedding_model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            print(f"Error generating embedding: {e}")
            raise e

    def generate_retention_email(self, user_profile: dict, policies: list[str]) -> str:
        """
        Generates a personalized retention email using Gemini.
        """
        feature_context = user_profile.get("features", {})
        user_id = user_profile.get("user_id", "Unknown")
        churn_prob = user_profile.get("churn_probability", 0.0)
        
        system_prompt = """
        你是一个高级客户关系专家 (SentinEL)。你的目标是根据数据和公司政策挽留高价值客户。
        严禁编造优惠政策，必须基于工具检索到的信息。
        语气要诚恳、专业且具有个性化。
        """
        
        # Format policies for the prompt
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
            return response.text
        except Exception as e:
            print(f"Error generating email: {e}")
            return "Unable to generate email at this time."
