from fastapi import FastAPI

from app.routers import employed

app = FastAPI(
    title="ORBIT FastAPI Server",
    description="ORBIT FASTAPI 서버",
    version="0.1.0"
)

app.include_router(employed.router)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": "fastapi"
    }
