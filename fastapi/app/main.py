from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.openapi import configure_openapi
from app.error_handlers import register_error_handlers
from app.repositories.employees_income_repository import ensure_data_available
from app.routers import employees, retirement


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_data_available()
    yield


app = FastAPI(
    title="ORBIT FastAPI Server",
    description="ORBIT FastAPI Server",
    version="0.1.0",
    root_path="/ai",
    lifespan=lifespan,
)

register_error_handlers(app)

app.include_router(employees.router)
app.include_router(retirement.router)
configure_openapi(app)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": "fastapi",
    }
