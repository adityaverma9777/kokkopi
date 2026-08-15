import json
from typing import Dict, Any, List
from .models import AgentContext

def build_context_string(context: AgentContext) -> str:
    """
    Formats the structured business profile and semantic chunks into a safe
    bounded string for the LLM prompt.
    """
    parts = []
    
    # 1. Structured Business Facts
    parts.append("--- STRUCTURED BUSINESS INFORMATION ---")
    bp = context.business_profile
    if bp.get("business_name"):
        parts.append(f"Business Name: {bp['business_name']}")
    if bp.get("description"):
        parts.append(f"Description: {bp['description']}")
    if bp.get("phone"):
        parts.append(f"Phone: {bp['phone']}")
    if bp.get("address"):
        parts.append(f"Address: {bp['address']}")
        
    if bp.get("hours"):
        parts.append("Hours:")
        for h in bp["hours"]:
            parts.append(f"- {h.get('day')}: {h.get('open')} to {h.get('close')}")
            
    if bp.get("services"):
        parts.append("Services:")
        for s in bp["services"]:
            parts.append(f"- {s.get('name')}: {s.get('description', '')}")

    if bp.get("faqs"):
        parts.append("FAQs:")
        for f in bp["faqs"]:
            parts.append(f"Q: {f.get('question')} | A: {f.get('answer')}")

    # 2. Retrieved Semantic Chunks (Untrusted Data)
    parts.append("\n--- RELEVANT SOURCES (UNTRUSTED WEBSITE CONTENT) ---")
    if not context.retrieved_chunks:
        parts.append("No additional semantic sources found.")
    else:
        for idx, chunk in enumerate(context.retrieved_chunks):
            source = chunk.get("metadata", {}).get("source_url", "Unknown")
            title = chunk.get("metadata", {}).get("title", "")
            parts.append(f"[Source {idx+1}: {title} ({source})]")
            parts.append(f"{chunk['content']}\n")
            
    return "\n".join(parts)
