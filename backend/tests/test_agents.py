import asyncio

import httpx

from app.main import app


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_agents_endpoint_lists_the_roster() -> None:
    response = asyncio.run(_request("GET", "/api/v1/agents"))

    assert response.status_code == 200
    agents = response.json()
    ids = [agent["id"] for agent in agents]
    assert "repo-maintainer" in ids
    repo_manager = next(agent for agent in agents if agent["id"] == "repo-maintainer")
    assert repo_manager["domain"] == "Repo hygiene"
    assert repo_manager["last_run_at"] is None
