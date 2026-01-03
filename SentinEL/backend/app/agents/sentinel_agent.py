import logging
import json
import operator
import traceback
from typing import TypedDict, Annotated, List, Any, Dict, Union, Optional

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_vertexai import ChatVertexAI
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.config import settings
from app.agents.tools import ALL_TOOLS

logger = logging.getLogger(__name__)

# ==============================================================================
# Agent State
# ==============================================================================

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    user_id: str

# ==============================================================================
# Trace Log Models (Internal Helper)
# ==============================================================================

class TraceStep(TypedDict):
    step: int
    type: str # "thought", "action", "observation"
    tool: str # Optional
    input: str # Optional
    content: str

# ==============================================================================
# Graph Construction
# ==============================================================================

def create_agent_graph():
    """
    Constructs the ReAct Agent Graph using LangGraph.
    """
    
    # 1. Initialize LLM with Tools
    llm = ChatVertexAI(
        project=settings.PROJECT_ID,
        location=settings.LOCATION,
        model_name="gemini-2.5-pro",  # 使用用户指定的稳定模型 (解决实验模型配额问题)
        temperature=0.0,
        max_output_tokens=2048,
    )
    
    tools = ALL_TOOLS
    llm_with_tools = llm.bind_tools(tools)
    
    # 2. Define Nodes
    
    def reason_node(state: AgentState):
        """
        The reasoning node (LLM) that decides what to do next.
        """
        messages = state.get("messages", [])
        
        # 确保消息列表非空
        if not messages:
            logger.warning("reason_node received empty messages list, creating initial prompt")
            user_id = state.get("user_id", "unknown")
            messages = [HumanMessage(content=f"请分析用户 {user_id} 的状态并制定挽留计划。")]
        
        # System Prompt Injection
        system_prompt = (
            "你是一个决策型 AI (SentinEL Agent)。"
            "你的目标是为用户制定最佳挽留策略。"
            "必须遵循以下决策逻辑："
            "1. 首先调用 lookup_user_profile 获取用户画像和最近行为。"
            "2. 然后调用 predict_churn_risk 获取流失概率。"
            "3. 评估风险：如果风险高（Risk Level = High 或 Score > 0.7），必须寻找挽留策略。"
            "4. [关键] 在分析高价值（VIP）流失用户时，必须调用 consult_market_intelligence 工具，查询当前的市场竞争环境（如竞品价格、热门新功能 "
            "   例如 'Competitor pricing 2025'）。如果发现竞品有降价活动，请在挽留邮件中提供更有竞争力的折扣。"
            "5. 调用 find_retention_strategies 获取候选策略。"
            "6. 对成本最高的策略，务必调用 check_budget_availability 确认预算。"
            "7. 如果预算不足或风险较低，仅建议发送关怀邮件或低成本策略。"
            "8. 每一步都要解释原因 (Thought)。"
            "9. 最终给出一个总结性的建议。"
            "\n"
            "**重要规则**: \n"
            "   a) 如果你收到了来自 Judge (评审员) 的反馈/批评，你必须根据反馈修改你之前的输出，认真解决反馈中提到的具体问题。不要重复之前的错误。\n"
            "   b) **输出语言限制**: 所有的思考 (Thought)、动作原因 (Action Input explanations)、以及**最终生成的邮件草稿 (Email Draft)**，"
            "都必须使用 **简体中文 (Simplified Chinese)**。即使用户的地区是海外 (如 Spain, USA)，你的分析报告和建议也是给中国运营团队看的，"
            "所以必须用中文。邮件草稿如果为了本地化需要外语，请提供中英(或中西)双语对照，或者优先提供中文版并在括号内说明'需翻译'。"
            "但为了本次演示，**请强制生成中文邮件**，以便运营人员直接审核。"
        )
        
        
        # Merge System Prompt into HumanMessage to avoid LangChain/VertexAI history parsing bugs
        # (References IndexError: list index out of range in _parse_chat_history_gemini)
        if messages and isinstance(messages[0], HumanMessage):
             original_content = messages[0].content
             messages[0] = HumanMessage(content=f"{system_prompt}\n\nUSER REQUEST: {original_content}")
        elif not messages:
             # Should not happen due to check above, but for safety
             user_id = state.get("user_id", "unknown") # Ensure user_id is defined for this branch
             messages = [HumanMessage(content=f"{system_prompt}\n\nUSER REQUEST: 分析用户 {user_id}")]
             
        try:
            logger.info(f"Invoking LLM with {len(messages)} messages.")
            for i, m in enumerate(messages):
                logger.info(f"Msg [{i}] Type: {type(m).__name__}, Content: {str(m.content)[:100]}...")
                if hasattr(m, 'tool_calls') and m.tool_calls:
                     logger.info(f"  Tool Calls: {m.tool_calls}")

            # Sanitize messages for Gemini
            sanitized_messages = []
            for m in messages:
                if isinstance(m, AIMessage) and m.tool_calls and not m.content:
                    # Gemini adapter requires content to be at least empty string, not None
                    m.content = ""
                sanitized_messages.append(m)
                
            response = llm_with_tools.invoke(sanitized_messages)
            return {"messages": [response]}
        except Exception as e:
            logger.error(f"LLM invoke failed: {e}", exc_info=True)
            # Create a fallback message to prevent crash loop
            error_trace = traceback.format_exc()
            return {"messages": [AIMessage(content=f"分析过程中遇到错误: {str(e)}\n\nTraceback:\n{error_trace[:500]}")]}

    def action_node(state: AgentState):
        """
        Executes the tools requested by the LLM.
        NOTE: LangGraph's prebuilt ToolNode is usually preferred, but we define it here for clarity 
        or if we need custom logging. We will use the prebuilt one for robustness.
        """
        pass # Placeholder, we use prebuilt ToolNode
        
    tool_node = ToolNode(tools)

    # 3. Define Conditional Logic
    
    def should_continue(state: AgentState):
        """
        Decides whether to continue (call tools) or end.
        """
        last_message = state["messages"][-1]
        
        if not isinstance(last_message, AIMessage):
             # Should not happen in this design
             return END
             
        if last_message.tool_calls:
            return "tools"
        else:
            return END

    # 4. Build Graph
    workflow = StateGraph(AgentState)
    
    workflow.add_node("agent", reason_node)
    workflow.add_node("tools", tool_node)
    
    workflow.set_entry_point("agent")
    
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
             END: END
        }
    )
    
    workflow.add_edge("tools", "agent")
    
    return workflow.compile()

# ==============================================================================
# Invocation & Log Parsing
# ==============================================================================

# Singleton Graph
_agent_graph = None

def get_agent_graph():
    global _agent_graph
    if not _agent_graph:
        _agent_graph = create_agent_graph()
    return _agent_graph

async def invoke_agent(user_id: str, feedback: Optional[str] = None, competitor_intelligence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    调用 Agent 并返回最终结果 + trace log。
    
    Args:
        user_id: 用户 ID
        feedback: 来自 Judge 的反馈 (可选)，用于重试时改进策略
        competitor_intelligence: 竞品情报数据 (可选)，包含 competitor_name, offer_price, offer_details, weakness
        
    Returns:
        Dict: 包含 final_result 和 trace_log
    """
    logger.info(f"Agent invoked for user_id={user_id} | has_feedback={feedback is not None} | has_competitor_intel={competitor_intelligence is not None}")
    
    # 构建初始消息
    initial_message = f"请分析用户 {user_id} 的状态并制定挽留计划。"
    
    # 如果有竞品情报，优先注入到消息中 (最高优先级上下文)
    if competitor_intelligence:
        competitor_context = f"""
**🔴 关键市场情报警报 (CRITICAL: Market Intelligence Detected)**

我们检测到用户正在考虑竞品的优惠：
- **竞品名称**: {competitor_intelligence.get('competitor_name', 'Unknown')}
- **竞品价格**: {competitor_intelligence.get('offer_price', 'N/A')}
- **优惠详情**: {competitor_intelligence.get('offer_details', '无详情')}
- **竞品弱点**: {competitor_intelligence.get('weakness', '未知')}

**你的挽留策略必须：**
1. **明确回应**这个竞品优惠，不能忽视。
2. 如果竞品价格更低，评估是否可以匹配或提供更高价值的替代方案。
3. **攻击竞品弱点**，突出我们的差异化优势。
4. 在生成的邮件中自然融入对竞品的反击，但不要直接贬低对手。
"""
        initial_message = f"{initial_message}\n\n{competitor_context}"
        logger.info(f"[Agent] 注入竞品情报: {competitor_intelligence.get('competitor_name')}, 价格: {competitor_intelligence.get('offer_price')}")
    
    # 如果有 Judge 反馈，追加到消息中
    if feedback:
        initial_message = (
            f"{initial_message}\n\n"
            f"**重要反馈**: \n{feedback}\n\n"
            f"请根据以上反馈重新制定更高质量的挽留策略。"
        )
        logger.info(f"[Agent] 注入 Judge 反馈: {feedback[:100]}...")
    
    inputs = {
        "messages": [HumanMessage(content=initial_message)],
        "user_id": user_id
    }
    
    # Run the graph
    graph = get_agent_graph()
    final_state = await graph.ainvoke(inputs)
    
    # Parse Trace Logs from Messages
    messages = final_state["messages"]
    trace_log: List[TraceStep] = []
    step_counter = 1
    
    for msg in messages:
        if isinstance(msg, AIMessage):
            # Thought: Content present
            if msg.content:
                trace_log.append({
                    "step": step_counter,
                    "type": "thought",
                    "content": str(msg.content),
                    "tool": None,
                    "input": None
                })
                step_counter += 1
            
            # Action: Tool Calls present
            if msg.tool_calls:
                for tool_call in msg.tool_calls:
                    trace_log.append({
                        "step": step_counter,
                        "type": "action",
                        "content": f"调用工具: {tool_call['name']}",
                        "tool": tool_call['name'],
                        "input": json.dumps(tool_call['args'], ensure_ascii=False)
                    })
                    step_counter += 1
                    
        elif isinstance(msg, ToolMessage):
            # Observation: Tool Output
            trace_log.append({
                "step": step_counter,
                "type": "observation",
                "content": str(msg.content), # Content is usually the tool output string
                "tool": msg.name,
                "input": None
            })
            step_counter += 1
            
    # Final Result is the last message content
    final_result = messages[-1].content if messages else "No reponse generated."
    
    return {
        "final_result": final_result,
        "trace_log": trace_log
    }
