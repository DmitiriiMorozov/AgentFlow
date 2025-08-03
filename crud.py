from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
import models

# Получить все задачи для конкретного пользователя
async def get_tasks_by_user(db: AsyncSession, user_id : int):
    query = select(models.Task).where(models.Task.user_id == user_id)
    result = await db.execute(query)
    return result.scalars().all()

# Создать новую задачу
async def create_task(db: AsyncSession, user_id : int, title: str):
    db_task = models.Task(user_id=user_id, title=title)
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

# Обновить задачу
async def update_task(db: AsyncSession, user_id: int, task_id: int, title: str, status: str):
    query = (
        update(models.Task)
        .where(models.Task.id == task_id, models.Task.user_id == user_id)
    )
    if title:
        query = query.values(title=title)
    if status:
        query = query.values(status=status)
    await db.execute(query)
    await db.commit()
    updated_task = await db.get(models.Task, task_id)
    return updated_task

# Удалить задачу
async def remove_task(db: AsyncSession, user_id: int, task_id: int):
    task_to_delete = await db.get(models.Task, task_id)
    if task_to_delete and task_to_delete.user_id == user_id:
        await db.delete(task_to_delete)
        await db.commit()
        return True
    return False

# Очистить все задачи пользователя
async def clear_all_tasks(db: AsyncSession, user_id: int):
    query = (
        delete(models.Task)
        .where(models.Task.user_id == user_id)
    )
    result = await db.execute(query)
    await db.commit()
    return result.rowcount