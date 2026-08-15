import asyncio
import httpx

async def main():
    print("--- KOKKOPI MVP PHASE 2 DEMONSTRATION ---")
    # Note: Requires the FastAPI server running on http://127.0.0.1:8000
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        print("\n1. Registering Tenant A...")
        resp = await client.post("/api/auth/register", json={
            "email": "a@example.com",
            "password": "pass",
            "company_name": "Company A"
        })
        print(resp.json())
        token_a = resp.json().get("access_token")
        headers_a = {"Authorization": f"Bearer {token_a}"}

        print("\n2. Registering Tenant B...")
        resp = await client.post("/api/auth/register", json={
            "email": "b@example.com",
            "password": "pass",
            "company_name": "Company B"
        })
        print(resp.json())
        token_b = resp.json().get("access_token")
        headers_b = {"Authorization": f"Bearer {token_b}"}

        print("\n3. Tenant A Creating Agent...")
        resp = await client.post("/api/agents", json={
            "name": "Smart Buddy",
            "type": "chat_voice"
        }, headers=headers_a)
        print(resp.json())
        agent_id = resp.json().get("id")

        print("\n4. Tenant A Retrieving Agent...")
        resp = await client.get(f"/api/agents/{agent_id}", headers=headers_a)
        print(f"Status: {resp.status_code} - Name: {resp.json().get('name')}")

        print("\n5. Tenant B Attempting Cross-Tenant Access to Agent A...")
        resp = await client.get(f"/api/agents/{agent_id}", headers=headers_b)
        print(f"Status: {resp.status_code} - Detail: {resp.json()}")

if __name__ == "__main__":
    asyncio.run(main())
