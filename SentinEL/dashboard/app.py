import streamlit as st
import requests
import pandas as pd
import json

# ==============================================================================
# 配置与常量
# ==============================================================================
st.set_page_config(
    layout="wide",
    page_title="SentinEL系统监控台",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': "# SentinEL AI User Retention System"
    }
)

API_URL = "https://sentinel-agent-service-672705370432.us-central1.run.app/analyze_user"

# ==============================================================================
# 自定义 CSS (深色科技风)
# ==============================================================================
st.markdown("""
<style>
    /* 全局背景色 */
    .stApp {
        background-color: #0e1117;
    }
    
    /* 侧边栏背景 */
    section[data-testid="stSidebar"] {
        background-color: #161b22;
    }
    
    /* 卡片/容器样式 */
    div.css-1r6slb0, div.stMetric {
        background-color: #21262d;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
    }
    
    /* 标题颜色 */
    h1, h2, h3 {
        color: #58a6ff !important;
        font-family: 'Segoe UI', sans-serif;
    }
    
    /* 文本颜色 */
    div, p, span {
        color: #c9d1d9;
    }
    
    /* JSON展示背景 */
    .stJson {
        background-color: #0d1117;
    }
    
    /* 按钮样式 */
    .stButton > button {
        background-color: #238636;
        color: white;
        border: none;
        padding: 10px 24px;
        border-radius: 6px;
        font-weight: 600;
        width: 100%;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background-color: #2ea043;
        box-shadow: 0 0 10px rgba(46, 160, 67, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==============================================================================
# 侧边栏: 系统状态
# ==============================================================================
with st.sidebar:
    st.title("🛡️ SentinEL System")
    st.markdown("---")
    
    st.subheader("System Status")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Model Status", "🟢 Online")
    with col2:
        st.metric("Vector DB", "🔗 Connected")
        
    st.markdown("---")
    st.markdown("### 🏗️ Architecture")
    st.info("FastAPI (Cloud Run) + Gemini 1.5 Pro + BigQuery")
    
    st.markdown("---")
    st.caption("v1.0.0 | Developed by Achilles")

# ==============================================================================
# 主界面: 顶部输入区
# ==============================================================================
st.title("🚨 风险用户干预中心 (Intervention Center)")
st.markdown("通过 AI 实时分析用户行为，并生成个性化挽留策略。")

with st.container():
    col_input, col_btn = st.columns([3, 1])
    
    with col_input:
        user_id = st.text_input("User ID", value="63826", help="输入需要分析的用户ID")
        
    with col_btn:
        st.write("") # Spacer for alignment
        st.write("") 
        start_btn = st.button("🚀 启动智能分析 (Start Analysis)")

# ==============================================================================
# 主界面: 分析结果区
# ==============================================================================
if start_btn:
    if not user_id:
        st.error("请输入 User ID")
    else:
        try:
            with st.spinner(f"🔍 AI 正在分析用户 {user_id} 的行为模式..."):
                response = requests.post(API_URL, json={"user_id": user_id})
                
            if response.status_code == 200:
                data = response.json()
                
                st.success("✅ 分析完成！")
                st.markdown("---")
                
                # 三列布局展示结果
                col_profile, col_rag, col_action = st.columns(3)
                
                # 第一列: 用户画像
                with col_profile:
                    st.subheader("👤 用户画像 (User Profile)")
                    
                    risk_level = data.get("risk_level", "Unknown")
                    churn_prob = data.get("churn_probability", 0.0)
                    
                    # 颜色编码
                    delta_color = "inverse" if churn_prob > 0.5 else "normal"
                    
                    c1, c2 = st.columns(2)
                    with c1:
                         st.metric("流失概率", f"{churn_prob:.1%}", delta_color=delta_color)
                    with c2:
                         st.metric("风险等级", risk_level)
                    
                    st.markdown("#### 特征数据 (Features)")
                    st.json(data.get("user_features", {}))

                # 第二列: RAG 思考
                with col_rag:
                    st.subheader("🧠 检索到的策略 (RAG Memory)")
                    policies = data.get("retention_policies", [])
                    
                    if not policies:
                        st.warning("未检索到特定策略")
                    else:
                        for i, policy in enumerate(policies, 1):
                            st.info(f"**策略 #{i}**\n\n{policy}")

                # 第三列: AI 行动
                with col_action:
                    st.subheader("📧 生成的挽留邮件 (AI Action)")
                    email_content = data.get("generated_email", "无内容生成")
                    
                    st.markdown(f"""
                    <div style='background-color: #1e1e1e; padding: 20px; border-radius: 5px; border-left: 5px solid #238636;'>
                        {email_content}
                    </div>
                    """, unsafe_allow_html=True)
                    
            else:
                st.error(f"❌ API 请求失败: {response.status_code}")
                st.code(response.text)
                
        except Exception as e:
            st.error(f"❌ 连接发生错误: {str(e)}")
            st.info("请检查后台服务是否已启动或网络连接。")
