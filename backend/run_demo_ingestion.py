import asyncio
import httpx
import time

async def main():
    print("--- KOKKOPI MVP PHASE 3 DEMONSTRATION ---")
    base_url = "http://127.0.0.1:8000"
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        # 1. Login or Register
        resp = await client.post("/api/auth/register", json={
            "email": "demo3@example.com",
            "password": "pass",
            "company_name": "Demo 3 Corp"
        })
        if resp.status_code == 400: # Already registered
            resp = await client.post("/api/auth/login", json={
                "email": "demo3@example.com",
                "password": "pass"
            })
            
        token = resp.json().get("access_token")
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Create Agent
        resp = await client.post("/api/agents", json={
            "name": "Fixture Agent",
            "type": "chat"
        }, headers=headers)
        agent_id = resp.json().get("id")
        print(f"Agent Created: {agent_id}")

        # 3. Submit Ingestion
        print("\nSubmitting Ingestion for Local Fixture...")
        ingest_resp = await client.post(f"/api/agents/{agent_id}/ingest", json={
            "sitemap_url": "http://localhost:8080/sitemap.xml",
            "consent": True
        }, headers=headers)
        
        job_id = ingest_resp.json().get("job_id")
        print(f"Job Queued: {job_id}")
        
        # 4. Wait for Job
        print("\nPolling Job Status...")
        while True:
            status_resp = await client.get(f"/api/agents/{agent_id}/ingest/{job_id}", headers=headers)
            data = status_resp.json()
            print(f"Status: {data['status']} | Discovered: {data['total_discovered']} | Processed: {data['total_processed']} | Failed: {data['total_failed']}")
            
            if data['status'] in ["completed", "failed", "cancelled"]:
                break
            await asyncio.sleep(2)
            
        # 5. Inspect Knowledge
        print("\n--- Business Profile ---")
        prof_resp = await client.get(f"/api/agents/{agent_id}/profile", headers=headers)
        print(prof_resp.json())
        
        print("\n--- Sources ---")
        src_resp = await client.get(f"/api/agents/{agent_id}/sources", headers=headers)
        print(f"Found {len(src_resp.json())} sources")
        
        print("\n--- Chunks ---")
        chunk_resp = await client.get(f"/api/agents/{agent_id}/knowledge", headers=headers)
        chunks = chunk_resp.json()
        print(f"Found {len(chunks)} chunks.")
        if chunks:
            print(f"Sample Chunk: {chunks[0]['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())
