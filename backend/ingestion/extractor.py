import json
from bs4 import BeautifulSoup
from typing import Dict, Any, List

def extract_json_ld(soup: BeautifulSoup) -> List[Dict]:
    """Extracts all JSON-LD blocks from the HTML."""
    json_lds = []
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string)
            if isinstance(data, list):
                json_lds.extend(data)
            else:
                json_lds.append(data)
        except Exception:
            continue
    return json_lds

def extract_business_profile(html_contents: List[str]) -> Dict[str, Any]:
    """
    Given a list of HTML pages from the site, attempts to deterministically
    extract a BusinessProfile.
    """
    profile = {
        "business_name": None,
        "description": None,
        "phone": None,
        "email": None,
        "address": None,
        "hours": [],
        "services": []
    }
    
    # 1. Look for Schema.org / JSON-LD first
    all_json_ld = []
    for html in html_contents:
        soup = BeautifulSoup(html, "html.parser")
        all_json_ld.extend(extract_json_ld(soup))
        
    for data in all_json_ld:
        # Check if it's a LocalBusiness or Organization
        if data.get("@type") in ["LocalBusiness", "Organization", "MedicalBusiness", "Store", "Dentist"]:
            if not profile["business_name"]:
                profile["business_name"] = data.get("name")
            if not profile["description"]:
                profile["description"] = data.get("description")
            if not profile["phone"]:
                profile["phone"] = data.get("telephone")
                
            address = data.get("address")
            if address and isinstance(address, dict):
                parts = [address.get("streetAddress"), address.get("addressLocality"), address.get("postalCode"), address.get("addressCountry")]
                profile["address"] = ", ".join([p for p in parts if p])
                
            hours = data.get("openingHoursSpecification")
            if hours and isinstance(hours, list):
                for h in hours:
                    days = h.get("dayOfWeek", [])
                    if isinstance(days, str):
                        days = [days]
                    for day in days:
                        profile["hours"].append({
                            "day": day,
                            "open": h.get("opens"),
                            "close": h.get("closes")
                        })
                        
    # For MVP, we use deterministic JSON-LD. If we wanted an LLM fallback,
    # we would pass the cleaned text of the 'Contact' or 'About' page to Groq here.
    return profile
