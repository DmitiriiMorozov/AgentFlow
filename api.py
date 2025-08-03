from fastapi import FastAPI, HTTPException, Path, Body, status, Depends, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
import crud, models, database
from database import engine, Base, get_async_db

class TaskOut(BaseModel):
    id: int
    title: str
    status: str

    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)

class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None)

app = FastAPI(
    title="AgentFlow API",
    version="1.0",
    description="Асинхронный API для управления задачами с использованием FastAPI и SQLAlchemy."
)

VALID_STATUSES = {"new", "done"}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

def verify_user_exists(user_id: int = Path(..., gt=0, description="ID пользователя должен быть положительным числом")):
    return user_id


@app.get("/", tags=["Root"], summary="Проверка работы API")
def root():
    """
    Корневой эндпоинт для проверки, что сервис запущен и работает.
    """
    return {"message": "AgentFlow API работает"}

@app.get("/users/{user_id}/tasks", response_model=List[TaskOut], tags=["Tasks"], summary="Получить список задач пользователя")
async def get_tasks(
    user_id: int = Depends(verify_user_exists),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список всех задач для указанного пользователя.
    """
    tasks = await crud.get_tasks_by_user(db=db, user_id=user_id)
    return tasks

@app.post("/users/{user_id}/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED, tags=["Tasks"], summary="Создать новую задачу")
async def create_task(
    task : TaskCreate,
    user_id: int = Depends(verify_user_exists),
    db: AsyncSession = Depends(get_async_db)    
):
    """
    Создает новую задачу для пользователя с указаныым 'user_id'.
    """
    new_task = await crud.create_task(db=db, user_id=user_id, title=task.title)
    return new_task

@app.patch("/users/{user_id}/tasks/{task_id}", response_model=TaskOut, tags=["Tasks"], summary="Обновить задачу")
async def patch_task(
    task_update: TaskUpdate,
    user_id: int = Depends(verify_user_exists),
    task_id: int = Path(..., gt=0, description="ID задачи для обновления"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет заголовок и/или статус существующей задачи.
    """
    if not task_update.title and not task_update.status:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Нет данных для обновления")
    if task_update.status and task_update.status not in VALID_STATUSES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Недопустимый статус. Используйте: {','.join(VALID_STATUSES)}")
    updated_task = await crud.update_task(
        db=db,
        user_id=user_id,
        task_id=task_id,
        title=task_update.title,
        status=task_update.status
    )
    if updated_task is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена или не принадлежит пользователю")
    return updated_task

@app.delete("/users/{user_id}/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tasks"], summary="Удалить конкретную задачу")
async def delete_task(
    user_id: int = Depends(verify_user_exists),
    task_id: int = Path(..., gt=0, description="ID задачи для удаления"),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Удаляет одну задачу по ее ID.
    """
    success = await crud.remove_task(db=db, user_id = user_id, task_id=task_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Задача не найдена или не принадлежит пользователю")
    return None

@app.delete("/users/{user_id}/tasks", response_model=dict, tags=["Tasks"], summary="Удалить все задачи пользователя")
async def clear_tasks(
    user_id: int = Depends(verify_user_exists),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Удаляет все задачи для указанного пользователя.
    """
    tasks = await crud.get_tasks_by_user(db, user_id)
    if len(tasks) > 50:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Нельзя удалить более 50 задач за раз")
    deleted_count = await crud.clear_all_tasks(db=db, user_id=user_id)
    return {"message": f"{deleted_count} задач пользователя {user_id} было удалено."}