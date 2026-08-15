from bs4 import BeautifulSoup
import re

def clean_html(html_content: str) -> str:
    """
    Cleans HTML to extract meaningful business text and structure.
    Removes scripts, styles, navs, and boilerplate.
    Returns cleaned text.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Remove unwanted tags
    unwanted_tags = [
        "script", "style", "noscript", "nav", "footer", 
        "header", "aside", "iframe", "svg", "canvas",
        "form"
    ]
    for tag in soup.find_all(unwanted_tags):
        tag.decompose()
        
    # Get text with newlines to preserve some structure
    # Use a separator to keep paragraphs distinct
    text = soup.get_text(separator="\n\n", strip=True)
    
    # Normalize multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text
