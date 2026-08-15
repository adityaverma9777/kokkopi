import pytest
from backend.ingestion.cleaner import clean_html
from backend.ingestion.extractor import extract_business_profile
from backend.ingestion.chunker import chunk_text
from backend.ingestion.embeddings import SentenceTransformerProvider

def test_cleaner_removes_scripts_and_styles():
    raw_html = """
    <html>
        <head>
            <script>console.log("bad");</script>
            <style>body { color: red; }</style>
        </head>
        <body>
            <nav>Menu</nav>
            <h1>Main Title</h1>
            <p>Some text.</p>
            <footer>Copyright</footer>
        </body>
    </html>
    """
    clean_txt = clean_html(raw_html)
    assert "bad" not in clean_txt
    assert "Menu" not in clean_txt
    assert "Copyright" not in clean_txt
    assert "Main Title" in clean_txt
    assert "Some text." in clean_txt

def test_extractor_json_ld():
    raw_html = """
    <html>
        <script type="application/ld+json">
        {
          "@type": "LocalBusiness",
          "name": "Test Dental",
          "telephone": "123456789"
        }
        </script>
    </html>
    """
    profile = extract_business_profile([raw_html])
    assert profile["business_name"] == "Test Dental"
    assert profile["phone"] == "123456789"

def test_chunking_logic():
    text = "Paragraph 1.\n\nParagraph 2."
    chunks = chunk_text(text, source_url="http://test.com")
    # For small texts, it might group them or split depending on max tokens.
    assert len(chunks) > 0
    assert "Paragraph 1." in chunks[0].content

@pytest.mark.asyncio
async def test_embedding_provider_shape():
    provider = SentenceTransformerProvider() # Default all-MiniLM-L6-v2
    # In a real CI, we might mock this or assure the model is downloaded
    # We just test the interface works and returns 384 dimensions for single item
    vectors = provider.embed_texts(["Hello world"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 384
