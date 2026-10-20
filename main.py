"""Punto de entrada de la API.

Levantar en local:  uvicorn main:app --reload
Swagger:            http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI

from tasks.routes import router as tasks_router
from users.routes import router as users_router

app = FastAPI(title="API de usuarios", version="0.1.0")
app.include_router(users_router)
app.include_router(tasks_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
