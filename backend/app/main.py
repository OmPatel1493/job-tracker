from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import applications, auth


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup: nothing needed yet — Alembic handles migrations
    yield
    # shutdown: close DB connection pool
    await engine.dispose()


app = FastAPI(
    title="Job Tracker API",
    description="AI-powered job application tracking backend.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(applications.router)


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
