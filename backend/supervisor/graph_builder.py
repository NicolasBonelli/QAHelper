import os
from typing import TypedDict
from typing import List
from langgraph.graph import StateGraph
from backend.utils.db_actions import save_message
# LangGraph expects a dict as state
# These are the following keys
# - input: user text
# - next_agent: string of the agent name that should handle the input
# - tool_response: result returned by the tool that the agent uses
# - final_output: final response from the system
# - current_agent: agent that just executed
# - supervisor_decision: supervisor's decision
# - messages: array with all conversation message history
from IPython.display import display, Image


class State(TypedDict):
    input: str
    next_agent: str
    tool_response: str
    final_output: str
    session_id: str
    current_agent: str
    supervisor_decision: str
    messages: List[dict]  # Array with message history
    executed_agents: List[str]  # Array with executed agents history

# Supervisor node that evaluates agent response and decides next step
from backend.supervisor.agent_supervisor import classify_with_gemini, supervise_agent_response

def supervisor_node(state):
    """
    Main supervisor node that:
    1. Receives the initial user input
    2. Decides which agent should handle the task
    3. Evaluates agent responses
    4. Decides whether to go to guardrail or delegate to another agent
    """
    user_input = state["input"]
    current_agent = state.get("current_agent", "")
    agent_response = state.get("tool_response", "")
    messages = state.get("messages", [])
    executed_agents = state.get("executed_agents", [])
    
    # If it's the first time (no current_agent), classify the initial input
    if not current_agent:
        # Add user message to history
        messages.append({
            "role": "user",
            "content": user_input,
            "timestamp": "initial"
        })
        
        # Classify initial input to determine the first agent
        agent = classify_with_gemini(user_input)
        
        return {
            "next_agent": agent,
            "messages": messages,
            "executed_agents": executed_agents
        }
    else:
        # Add agent response to history
        messages.append({
            "role": "agent",
            "agent": current_agent,
            "content": agent_response,
            "timestamp": "after_agent"
        })
        
        # Add current agent to executed agents history
        if current_agent not in executed_agents:
            executed_agents.append(current_agent)
        
        # Supervisor evaluates the response and decides the next step
        decision = supervise_agent_response(user_input, current_agent, agent_response, messages, executed_agents)
        
        return {
            "supervisor_decision": decision,
            "next_agent": decision if decision != "guardrail" else "",
            "messages": messages,
            "executed_agents": executed_agents
        }

# Message logging nodes
def log_user_message_node(state):
    try:
        save_message(state["session_id"], "user", state["input"])
    except Exception as e:
        print("[LogUser Error]", e)
    return {}  

def log_agent_response_node(state):
    try:
        save_message(state["session_id"], "agent", state["tool_response"])
    except Exception as e:
        print("[LogAgent Error]", e)
    return {}

# Finalization node
# Saves the agent's final response
# (before optionally passing it through Guardrails)
def finalize_output(state):
    print(state)
    return {
        "final_output": state.get("final_output")
    }


from backend.agents.rag_agent import rag_agent_node
from backend.agents.sentiment_agent import sentiment_agent_node
from backend.agents.email_agent import email_agent_node
from backend.agents.tech_agent import tech_agent_node

# Graph construction
builder = StateGraph(State)


from backend.moderation.guardrail import apply_toxic_guardrail_and_store

def guardrail_node(state: dict) -> dict:
    """
    Guardrail node that processes all message history,
    generates a coherent final response and validates it
    """
    
    return apply_toxic_guardrail_and_store(state)


builder.add_node("guardrail", guardrail_node)
builder.add_node("supervisor", supervisor_node)
builder.add_node("rag_agent", rag_agent_node)
builder.add_node("sentiment_agent", sentiment_agent_node)
builder.add_node("email_agent", email_agent_node)
builder.add_node("tech_agent", tech_agent_node)
builder.add_node("finalize", finalize_output)

# Graph flow - SUPERVISOR IS THE ENTRY POINT
builder.set_entry_point("supervisor")

# Function to route from supervisor
def route_from_supervisor(state: State) -> str:
    # If there's no current_agent, it's the first time and goes to an agent
    if not state.get("current_agent"):
        return state["next_agent"]
    else:
        # If there's already an executed agent, evaluate supervisor's decision
        decision = state["supervisor_decision"]
        if decision == "guardrail":
            return "guardrail"
        else:
            return decision

# Supervisor decides whether to go to guardrail or another agent
builder.add_conditional_edges(
    "supervisor",
    route_from_supervisor,
    {
        "guardrail": "guardrail",
        "rag_agent": "rag_agent",
        "sentiment_agent": "sentiment_agent",
        "email_agent": "email_agent",
        "tech_agent": "tech_agent",
    },
)

# Each agent goes to supervisor after completing its task
builder.add_edge("rag_agent", "supervisor")
builder.add_edge("sentiment_agent", "supervisor")
builder.add_edge("email_agent", "supervisor")
builder.add_edge("tech_agent", "supervisor")

# Guardrail goes to the end
builder.add_edge("guardrail", "finalize")

# Final graph node
builder.set_finish_point("finalize")

# Compile graph
app = builder.compile()

if __name__ == "__main__":
   
    
    # Generate and display graph diagram
    print("\n📈 GENERATING GRAPH DIAGRAM...")
    try:
        # Create directory if it doesn't exist
        os.makedirs("output", exist_ok=True)
        
        # Generate graph image
        graph_image = app.get_graph().draw_mermaid_png()
        
        # Save image
        with open("output/supervisor_architecture.png", "wb") as f:
            f.write(graph_image)
        
        print("✅ Diagram saved in: output/supervisor_architecture.png")
        
        try:
            display(Image(graph_image))
            print("📊 Diagram displayed in Jupyter")
        except:
            print("📊 Diagram generated (cannot be displayed in this environment)")
            
    except Exception as e:
        print(f"❌ Error generating diagram: {e}")
    
    
   
    

    
