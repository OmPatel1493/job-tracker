from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://192.168.2.168:3000",
        "http://192.168.2.168:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth.router)
app.include_router(applications.router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # WHY global handler: prevents raw 500 tracebacks leaking to the client;
    # returns a consistent JSON error shape instead.
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred."},
    )


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok"}
