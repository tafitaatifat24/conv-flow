"""LangGraph workflows for conversation processing."""
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, START, END

from conv_flow.llm_config import get_llm_model, get_structured_llm
from conv_flow.agents.schemas import (
    StageClassificationSchema,
    ConversationAnalysisSchema,
    CRMActionSuggesterSchema,
)


class StageClassificationState(TypedDict):
    """State for stage classification graph."""
    conversation_text: str
    result: StageClassificationSchema | None
    error: str | None


class ConversationAnalysisState(TypedDict):
    """State for conversation analysis graph."""
    conversation_text: str
    result: ConversationAnalysisSchema | None
    error: str | None


class CRMActionSuggesterState(TypedDict):
    """State for CRM action suggestion graph."""
    conversation_text: str
    stage: str | None
    analysis: dict | None
    result: CRMActionSuggesterSchema | None
    error: str | None


def create_stage_classification_graph():
    """
    Create and return a LangGraph for stage classification.
    
    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(StageClassificationState)
    
    def classify_stage(state: StageClassificationState) -> StageClassificationState:
        """Node: Classify conversation stage using LLM."""
        try:
            llm = get_llm_model()
            structured_llm = get_structured_llm(llm, StageClassificationSchema)
            
            prompt = f"""Analyze the following conversation and classify it into one of these stages:
- lead: New potential customer, initial inquiry
- prospect: Qualified lead showing interest
- negotiation: Terms and pricing being discussed
- qualified: Deal is viable and moving forward
- closed_won: Successfully closed deal
- closed_lost: Deal lost or rejected
- inactive: No activity or stalled

Conversation:
{state['conversation_text']}

Provide the stage, confidence score (0.0-1.0), and reasoning."""
            
            result = structured_llm.invoke(prompt)
            state["result"] = result
            
        except Exception as e:
            state["error"] = str(e)
        
        return state
    
    graph.add_node("classify", classify_stage)
    graph.add_edge(START, "classify")
    graph.add_edge("classify", END)
    
    return graph.compile()


def create_conversation_analysis_graph():
    """
    Create and return a LangGraph for conversation analysis.
    
    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(ConversationAnalysisState)
    
    def analyze_conversation(state: ConversationAnalysisState) -> ConversationAnalysisState:
        """Node: Analyze conversation using LLM."""
        try:
            llm = get_llm_model()
            structured_llm = get_structured_llm(llm, ConversationAnalysisSchema)
            
            prompt = f"""Analyze the following conversation and extract key information:

Conversation:
{state['conversation_text']}

Provide:
1. A concise 2-3 sentence summary
2. 3-5 key topics discussed
3. Overall sentiment (positive/negative/neutral)
4. Named entities (people, companies, products mentioned)
5. 2-4 suggested next actions
6. Confidence score for this analysis (0.0-1.0)"""
            
            result = structured_llm.invoke(prompt)
            state["result"] = result
            
        except Exception as e:
            state["error"] = str(e)
        
        return state
    
    graph.add_node("analyze", analyze_conversation)
    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", END)
    
    return graph.compile()


def create_crm_action_suggester_graph():
    """
    Create and return a LangGraph for CRM action suggestion.
    
    Returns:
        Compiled LangGraph
    """
    graph = StateGraph(CRMActionSuggesterState)
    
    def suggest_crm_actions(state: CRMActionSuggesterState) -> CRMActionSuggesterState:
        """Node: Suggest CRM actions based on conversation and analysis."""
        try:
            llm = get_llm_model()
            structured_llm = get_structured_llm(llm, CRMActionSuggesterSchema)
            
            analysis_context = ""
            if state.get("analysis"):
                analysis_context = f"\nPrevious analysis: {state['analysis']}"
            
            stage_context = ""
            if state.get("stage"):
                stage_context = f"\nDetected stage: {state['stage']}"
            
            prompt = f"""Based on the following conversation, suggest specific CRM actions to take.

Conversation:
{state['conversation_text']}{stage_context}{analysis_context}

Suggest 2-4 relevant actions such as:
- follow_up: Schedule a follow-up email or call
- schedule_call: Schedule a meeting/call
- send_proposal: Send a proposal or quote
- update_status: Update opportunity status
- assign_task: Assign a task to team member
- custom: Any other action

For each action, provide:
1. Action type
2. Clear description of what to do
3. Suggested date/time (if applicable)
4. Priority (low/medium/high)
5. Reasoning

Mark requires_human_review as true if any action needs approval."""
            
            result = structured_llm.invoke(prompt)
            state["result"] = result
            
        except Exception as e:
            state["error"] = str(e)
        
        return state
    
    graph.add_node("suggest", suggest_crm_actions)
    graph.add_edge(START, "suggest")
    graph.add_edge("suggest", END)
    
    return graph.compile()


# Lazy initialization of graph instances
_stage_graph = None
_analysis_graph = None
_action_graph = None


def get_stage_classification_graph():
    """Get or create the stage classification graph."""
    global _stage_graph
    if _stage_graph is None:
        _stage_graph = create_stage_classification_graph()
    return _stage_graph


def get_conversation_analysis_graph():
    """Get or create the conversation analysis graph."""
    global _analysis_graph
    if _analysis_graph is None:
        _analysis_graph = create_conversation_analysis_graph()
    return _analysis_graph


def get_crm_action_suggester_graph():
    """Get or create the CRM action suggester graph."""
    global _action_graph
    if _action_graph is None:
        _action_graph = create_crm_action_suggester_graph()
    return _action_graph
