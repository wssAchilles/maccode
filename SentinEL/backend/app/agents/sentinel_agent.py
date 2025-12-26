import logging
import json
from typing import TypedDict, Annotated, List, Any, Dict, Union

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
    messages: Annotated[List[BaseMessage], "The conversation history"]
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
        model_name="gemini-pro", # Or gemini-1.5-pro-preview-0409
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
        messages = state["messages"]
        
        # System Prompt Injection
        # We perform a check to ensure System Prompt is at the start or context is appropriately set
        # For a simple ReAct loop, we can prepend instructions if not present, 
        # but here we assume the initial message setup handles it or we do it here.
        
        system_prompt = (
            "你是一个决策型 AI (SentinEL Agent)。"
            "你的目标是为用户制定最佳挽留策略。"
            "必须遵循以下决策逻辑："
            "1. 首先调用 lookup_user_profile 获取用户画像和最近行为。"
            "2. 然后调用 predict_churn_risk 获取流失概率。"
            "3. 评估风险：如果风险高（Risk Level = High 或 Score > 0.7），必须寻找挽留策略。"
            "4. 调用 find_retention_strategies 获取候选策略。"
            "5. 对成本最高的策略，务必调用 check_budget_availability 确认预算。"
            "6. 如果预算不足或风险较低，仅建议发送关怀邮件或低成本策略。"
            "7. 每一步都要解释原因 (Thought)。"
            "8. 最终给出一个总结性的建议。"
        )
        
        # Ensure system prompt is considered. 
        # In strictly chat models, specific logic applies, but prepending a SystemMessage is standard.
        from langchain_core.messages import SystemMessage
        if not isinstance(messages[0], SystemMessage):
             messages = [SystemMessage(content=system_prompt)] + messages
             
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

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
_agent_graph = create_agent_graph()

async def invoke_agent(user_id: str) -> Dict[str, Any]:
    """
    Invokes the agent and returns the final result + trace log.
    """
    logger.info(f"Agent invoked for user_id={user_id}")
    
    inputs = {
        "messages": [HumanMessage(content=f"请分析用户 {user_id} 的状态并制定挽留计划。")],
        "user_id": user_id
    }
    
    # Run the graph
    final_state = await _agent_graph.ainvoke(inputs)
    
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
