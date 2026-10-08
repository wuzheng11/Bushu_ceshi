from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import init_db
from .routers import admin, attachment, auth, chat, configs, results, tasks
from .services.config_service import config_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.ensure_directories()
    init_db()
    config_service.seed_defaults()
    yield


app = FastAPI(
    title="经营归因分析系统 API",
    version="1.0.0",
    description="支持 OAuth2 授权码登录、实时分析、工具调用、结果导出和配置热更新。",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(attachment.router)
app.include_router(tasks.router)
app.include_router(results.router)
app.include_router(configs.router)
app.include_router(admin.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "business-attribution-backend"}
