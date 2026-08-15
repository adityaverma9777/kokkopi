from typing import Dict, Any
from .models import AgentContext, AgentResponse

def check_no_answer(context: AgentContext, query: str) -> AgentResponse | None:
    """
    Checks if there is sufficient business knowledge to answer the query.
    If not, returns a controlled no-answer AgentResponse.
    If yes, returns None to proceed with LLM generation.
    """
    has_structured = any([
        context.business_profile.get("hours"),
        context.business_profile.get("services"),
        context.business_profile.get("prices"),
        context.business_profile.get("faqs"),
    ])
    
    # If we have neither relevant semantic chunks nor detailed structured facts, fallback.
    # We might allow basic greetings to pass to the LLM even without docs,
    # but for business queries we need evidence.
    
    greeting_keywords = ["hello", "hi", "hey", "who are you"]
    is_greeting = any(k in query.lower() for k in greeting_keywords)
    
    if not has_structured and not context.retrieved_chunks and not is_greeting:
        return get_no_answer_response(context)
        
    return None

def get_no_answer_response(context: AgentContext) -> AgentResponse:
    text = "I don't have that information from the business's published information."
    
    bp = context.business_profile
    if bp.get("phone") or bp.get("email"):
        contact = bp.get("phone") or bp.get("email")
        text += f" You can contact the business directly at {contact}."
        
    return AgentResponse(
        text=text,
        sources=[],
        grounded=False
    )
