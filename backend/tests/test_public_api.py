import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_public_api_blocks_missing_agent():
    # Since this relies on a real DB, we mock the dependency or test the failure path
    from backend.main import app
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.get("/api/public/agents/invalid_agent/config?session_id=123")
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_rate_limiting_enforced():
    from backend.api.routers.rate_limiter import check_rate_limit, RateLimitExceeded
    
    # Try 15 requests in loop (limit is 10 for chat)
    with pytest.raises(RateLimitExceeded):
        for _ in range(15):
            check_rate_limit("chat", "test_agt", "test_sess", max_requests=10, window_seconds=60)
