import httpx
import os
from typing import List, Dict, Optional

API_URL = os.getenv("API_URL", "http://api:8000")

class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=self.base_url)

    async def _request(self, method: str, path: str, **kwargs):
        try:
            response = await self.client.request(method, path, **kwargs)
            response.raise_for_status()
            return response
        except httpx.HTTPStatusError as e:
            print(f"API Error: {e.response.status_code} - {e.response.text}")
            raise e
        except httpx.RequestError as e:
            print(f"Request Error: {e}")
            raise e
    
    async def get_tasks(self, user_id: int) -> List[Dict]:
        response = await self._request("GET", f"/users/{user_id}/tasks")
        return response.json()
    
    async def add_task(self, user_id: int, title: str) -> Dict:
        response = await self._request("POST", f"/users/{user_id}/tasks", json={"title": title})
        return response.json()
    
    async def update_task_status(self, user_id: int, task_id: int, status: str) -> Dict:
        response = await self._request("PATCH", f"/users/{user_id}/tasks/{task_id}", json={"status": status})
        return response.json()
    
    async def update_task_title(self, user_id: int, task_id: int, title: str) -> Dict:
        response = await self._request("PATCH", f"/users/{user_id}/tasks/{task_id}", json={"title": title})
        return response.json()

    async def remove_task(self, user_id: int, task_id: int):
        await self._request("DELETE", f"/users/{user_id}/tasks/{task_id}")

    async def clear_tasks(self, user_id: int):
        await self._request("DELETE", f"/users/{user_id}/tasks")