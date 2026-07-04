from fastapi import FastAPI

from app.routers import employees, retirement

app = FastAPI(
    title="ORBIT FastAPI Server",
    description="ORBIT FastAPI Server",
    version="0.1.0",
    root_path="/ai",
)

app.include_router(employees.router)
app.include_router(retirement.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": "fastapi",
    }
