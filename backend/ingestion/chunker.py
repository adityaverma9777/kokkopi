from typing import List, Dict, Any

class Chunk:
    def __init__(self, content: str, index: int, metadata: Dict[str, Any]):
        self.content = content
        self.index = index
        self.metadata = metadata

def chunk_text(text: str, source_url: str, title: str = "", max_tokens: int = 400) -> List[Chunk]:
    """
    Splits text by double newlines (paragraphs), combining them up to max_tokens.
    Uses a rough approximation of 1 token ~= 4 characters for MVP.
    """
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_length = 0
    chunk_index = 0
    
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
            
        p_len = len(p) // 4
        
        # If a single paragraph is too big, we should ideally split by sentence,
        # but for MVP we will just add it if current_chunk is empty, or start a new one.
        if current_length + p_len > max_tokens and current_chunk:
            # Yield current chunk
            chunks.append(Chunk(
                content="\n\n".join(current_chunk),
                index=chunk_index,
                metadata={"source_url": source_url, "title": title}
            ))
            chunk_index += 1
            current_chunk = [p]
            current_length = p_len
        else:
            current_chunk.append(p)
            current_length += p_len
            
    if current_chunk:
        chunks.append(Chunk(
            content="\n\n".join(current_chunk),
            index=chunk_index,
            metadata={"source_url": source_url, "title": title}
        ))
        
    return chunks
