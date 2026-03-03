"""
graph.py — ARIA LangGraph StateGraph
Full routing: delegator → specialist agents → confirmation → submit
"""
from langgraph.graph import StateGraph, END
from agents.state import AgentState
from agents.delegator import delegator_node
from agents.occurrence_agent import occurrence_agent_node, occurrence_submit_node
from agents.teddy_bear_agent import teddy_bear_agent_node, teddy_bear_submit_node
from agents.schedule_agent import schedule_agent_node, schedule_submit_node
from agents.checklist_agent import checklist_agent_node
from agents.general_agent import general_agent_node


# ─────────────────────────────────────────────
# ROUTING FUNCTIONS
# ─────────────────────────────────────────────

def route_after_delegator(state: AgentState) -> str:
    """Route to the correct specialist based on intent.
    Since the delegator now bypasses re-classification mid-form, the intent
    will already be the correct form intent when active_form is set."""
    intent = state.get("intent", "general")

    routing = {
        "occurrence_report":    "occurrence_agent",
        "teddy_bear":           "teddy_bear_agent",
        "shift_schedule":       "schedule_agent",
        "shift_change_request": "schedule_agent",
        "status_checklist":     "checklist_agent",
        "update_checklist":     "checklist_agent",
        "weather":              "general_agent",
        "general":              "general_agent",
    }
    return routing.get(intent, "general_agent")


def route_occurrence_agent(state: AgentState) -> str:
    """Loop or advance for the occurrence report form."""
    if state.get("confirmed"):
        return "occurrence_submit"
    missing = [f for f in state.get("required_fields", [])
               if not state.get("form_data", {}).get(f)]
    if missing or state.get("confirmation_pending"):
        return END  # Return response to user, wait for next message
    return END


def route_teddy_bear_agent(state: AgentState) -> str:
    if state.get("confirmed"):
        return "teddy_bear_submit"
    return END


def route_schedule_agent(state: AgentState) -> str:
    if state.get("confirmed") and state.get("active_form") == "shift_change":
        return "schedule_submit"
    return END


def route_checklist_agent(state: AgentState) -> str:
    return END


# ─────────────────────────────────────────────
# BUILD THE GRAPH
# ─────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("delegator",          delegator_node)
    graph.add_node("occurrence_agent",   occurrence_agent_node)
    graph.add_node("occurrence_submit",  occurrence_submit_node)
    graph.add_node("teddy_bear_agent",   teddy_bear_agent_node)
    graph.add_node("teddy_bear_submit",  teddy_bear_submit_node)
    graph.add_node("schedule_agent",     schedule_agent_node)
    graph.add_node("schedule_submit",    schedule_submit_node)
    graph.add_node("checklist_agent",    checklist_agent_node)
    graph.add_node("general_agent",      general_agent_node)

    # Entry point
    graph.set_entry_point("delegator")

    # Delegator → specialist
    graph.add_conditional_edges("delegator", route_after_delegator, {
        "occurrence_agent":  "occurrence_agent",
        "teddy_bear_agent":  "teddy_bear_agent",
        "schedule_agent":    "schedule_agent",
        "checklist_agent":   "checklist_agent",
        "general_agent":     "general_agent",
    })

    # Occurrence report routing
    graph.add_conditional_edges("occurrence_agent", route_occurrence_agent, {
        "occurrence_submit": "occurrence_submit",
        END: END,
    })
    graph.add_edge("occurrence_submit", END)

    # Teddy bear routing
    graph.add_conditional_edges("teddy_bear_agent", route_teddy_bear_agent, {
        "teddy_bear_submit": "teddy_bear_submit",
        END: END,
    })
    graph.add_edge("teddy_bear_submit", END)

    # Schedule routing
    graph.add_conditional_edges("schedule_agent", route_schedule_agent, {
        "schedule_submit": "schedule_submit",
        END: END,
    })
    graph.add_edge("schedule_submit", END)

    # Direct to END
    graph.add_edge("checklist_agent", END)
    graph.add_edge("general_agent",   END)

    return graph.compile()


# Compiled graph — imported by main.py
aria_graph = build_graph()
