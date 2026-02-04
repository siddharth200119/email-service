from fastapi import FastAPI
from src.api import main_router as APIRouter
from src.middlewares.logger import LoggingMiddleware
import os
from src.events import startup, shutdown
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup(app)
    try:
        yield
    finally:
        await shutdown(app)


app.add_middleware(LoggingMiddleware)

app.include_router(APIRouter)

if __name__ == "__main__":
    import uvicorn

    DEFAULT_PORT = "3030"
    try:
        port = int(os.environ.get("PORT", DEFAULT_PORT))
    except Exception:
        port = int(DEFAULT_PORT)

    uvicorn.run(
        "main:app",
        port=port,
        host=os.environ.get("HOST", "127.0.0.1"),
        reload=os.environ.get("ENV", "DEV") == "DEV",
    )
