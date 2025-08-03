import pytest

pytestmark = pytest.mark.asyncio

async def test_create_and_read_task(client):
    """
    Тестируем полный цикл: создание задачи и ее последующее чтение.
    """
    user_id = 123
    
    response_create = await client.post(
        f"/users/{user_id}/tasks",
        json={"title": "Test Task 1"}
    )
    assert response_create.status_code == 201
    created_task = response_create.json()
    assert created_task["title"] == "Test Task 1"
    assert "id" in created_task

    response_get = await client.get(f"/users/{user_id}/tasks")
    assert response_get.status_code == 200
    tasks_list = response_get.json()
    assert len(tasks_list) == 1
    assert tasks_list[0]["title"] == "Test Task 1"
    assert tasks_list[0]["id"] == created_task["id"]
