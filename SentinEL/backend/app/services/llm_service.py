"""
LLM Service - 企业级 Gemini 大模型服务

包含 OpenTelemetry 手动埋点，用于 Google Cloud Trace 可视化。
"""

import vertexai
from vertexai.generative_models import GenerativeModel, Image, Part
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

    def generate_retention_email(
        self, 
        user_profile: dict, 
        policies: list[str], 
        image_bytes: bytes = None,
        model_name: str = None
    ) -> str:
        """
        使用 Gemini 生成个性化挽留邮件。
        支持多模态输入 (Competitor Image Analysis) 和 A/B 测试动态模型。
        
        Args:
            user_profile: 用户画像
            policies: 挽留政策列表
            image_bytes: 可选的图片数据
            model_name: 可选的模型名称 (A/B 测试用)
        
        Trace Span: "Gemini: Generate Email"
        """
        # 创建追踪 Span
        with tracer.start_as_current_span("Gemini: Generate Email") as span:
            # 动态选择模型 (A/B 测试支持)
            if model_name:
                active_model = GenerativeModel(model_name)
                actual_model_name = model_name
            else:
                active_model = self.generative_model
                actual_model_name = self.llm_model_name
            
            span.set_attribute("ai.model", actual_model_name)
            span.set_attribute("ai.provider", "vertex_ai")
            span.set_attribute("input.policies_count", len(policies))
            span.set_attribute("input.has_image", image_bytes is not None)
            
            feature_context = user_profile.get("features", {})
            user_id = user_profile.get("user_id", "Unknown")
            churn_prob = user_profile.get("churn_probability", 0.0)
            
            span.set_attribute("user.id", user_id)
            span.set_attribute("user.churn_probability", churn_prob)
            
            system_prompt = """
            你是一个高级客户关系专家 (SentinEL)。你的目标是根据数据和公司政策挽留高价值客户。
            严禁编造优惠政策，必须基于工具检索到的信息。
            语气要诚恳、专业且具有个性化。
            
            【重要输出指令】
            1. 仅输出邮件正文内容。
            2. 不要包含任何开场白（如"好的，这是邮件..."）或结束语。
            3. 不要包含 "Subject:" 主题行。
            4. 直接以称呼（如"Dear..."）开始。

            【多模态指令】
            如果提供了图片，那通常是用户上传的"竞争对手优惠/广告"或"客户投诉截图"。
            请先敏锐地分析图片中的关键信息（如通过图片看出对手提供了50%折扣，或客户在投诉物流）。
            并在生成的邮件中，针对性地回应这些视觉信息（例如："我们可以匹配该折扣"或"针对您提到的物流问题..."），但不要直接说"我看你传的图片..."，要自然融入。
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
                "max_output_tokens": 4096, # Increased for detailed analysis and full email generation
            }
            
            try:
                inputs = [system_prompt, user_prompt]
                
                # 如果有图片，加入到输入中
                if image_bytes:
                    print("Processing image for Vision API...")
                    image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg") # Default to jpeg, robust enough
                    inputs.append(image_part)
                    inputs.append("请参考上述图片中的竞争对手信息或问题进行针对性回复。")

                response = active_model.generate_content(
                    inputs,
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
                return "Unable to generate email at this time due to system error."

    def generate_call_script(self, email_content: str) -> str:
        """
        基于生成的邮件内容，提炼一段简短的电话留言脚本 (Voicemail Script)。
        风格：亲切、口语化。
        """
        with tracer.start_as_current_span("Gemini: Generate Script") as span:
             prompt = f"""
             Based on the following retention email, create a SHORT, CASUAL voicemail script (max 50 words).
             It should sound like a friendly account manager leaving a message.
             
             CRITICAL INSTRUCTIONS:
             1. The script MUST be in the SAME LANGUAGE as the email content (which is likely Simplified Chinese).
             2. If the email content is incomplete or truncated, infer the missing parts based on the context of a retention offer.
             3. Do not include "Subject:" or placeholders. 
             4. Just the spoken script.
             
             Email Context:
             {email_content}
             """
             
             try:
                response = self.generative_model.generate_content(prompt)
                return response.text.strip()
             except Exception as e:
                 print(f"Error generating script: {e}")
                 return "Hi, this is your account manager from SentinEL. We noticed you haven't been active lately and have a special offer for you. Please check your email!"

    def analyze_image(self, image_bytes: bytes, prompt: str = None) -> dict:
        """
        使用 Gemini 2.0 Flash 进行视觉分析，提取竞品优惠截图中的关键情报。
        
        Args:
            image_bytes: 图片二进制数据
            prompt: 可选的自定义 Prompt (默认使用竞品分析 Prompt)
        
        Returns:
            dict: 包含 competitor_name, offer_price, offer_details, weakness 的结构化数据
        
        Trace Span: "Gemini: Analyze Image"
        """
        with tracer.start_as_current_span("Gemini: Analyze Image") as span:
            span.set_attribute("ai.model", "gemini-2.0-flash-exp")
            span.set_attribute("ai.provider", "vertex_ai")
            span.set_attribute("input.image_size_bytes", len(image_bytes))
            
            # 使用视觉模型 (gemini-2.0-flash-exp 支持 Vision)
            vision_model = GenerativeModel("gemini-2.0-flash-exp")
            
            # 将图片字节转换为 Part
            image_part = Part.from_data(data=image_bytes, mime_type="image/jpeg")
            
            # 默认竞品分析 Prompt
            if not prompt:
                prompt = """你是一个精准的市场情报分析师。请仔细分析这张竞争对手的优惠活动截图，并提取以下关键信息。

**你必须严格按照以下 JSON 格式输出，不要添加任何额外的文字说明或 markdown 代码块标记：**

{
    "competitor_name": "竞品公司/产品名称 (如无法识别则填 'Unknown')",
    "offer_price": "优惠价格 (保留货币符号，如 '$19.99' 或 '¥99'，无法识别则填 'N/A')",
    "offer_details": "优惠的关键条款/限制 (如 '限时3天'、'新用户专享'、'不含XX服务')",
    "weakness": "基于此优惠推测的竞品弱点或我方可利用的反击点 (如 '价格低但服务缺失'、'短期促销难持续')"
}

注意：
1. 如果图片模糊或信息不完整，尽可能推断，并在相应字段注明不确定性。
2. offer_details 应尽可能详细列出所有限制条件。
3. weakness 需要有商业洞察力，帮助销售团队制定反击策略。
4. **所有字段的值必须使用简体中文输出。**"""
            
            generation_config = {
                "temperature": 0.1,  # 低温度确保结构化输出稳定
                "max_output_tokens": 1024,
            }
            
            try:
                response = vision_model.generate_content(
                    [prompt, image_part],
                    generation_config=generation_config
                )
                
                result_text = response.text.strip()
                span.set_attribute("output.raw_length", len(result_text))
                
                # 尝试解析 JSON
                import json
                import re
                
                # 清理可能的 markdown 代码块标记
                cleaned_text = result_text
                if cleaned_text.startswith("```"):
                    # 移除 ```json 和 ``` 标记
                    cleaned_text = re.sub(r'^```(?:json)?\s*', '', cleaned_text)
                    cleaned_text = re.sub(r'\s*```$', '', cleaned_text)
                
                try:
                    parsed_result = json.loads(cleaned_text)
                    span.set_attribute("output.parsed", True)
                    return parsed_result
                except json.JSONDecodeError as je:
                    # 如果 JSON 解析失败，返回原始文本包装
                    span.set_attribute("output.parsed", False)
                    span.set_attribute("error.json_parse", str(je))
                    return {
                        "competitor_name": "解析失败",
                        "offer_price": "N/A",
                        "offer_details": result_text[:200],
                        "weakness": "无法解析图片内容，建议人工审核",
                        "raw_response": result_text
                    }
                    
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                print(f"[LLMService] Image analysis failed: {e}")
                return {
                    "competitor_name": "分析失败",
                    "offer_price": "N/A",
                    "offer_details": f"错误: {str(e)}",
                    "weakness": "系统错误，请稍后重试",
                    "error": str(e)
                }

