from fastapi import FastAPI

from app.routers import active

app = FastAPI(
    title="ORBIT FastAPI Server",
    description="ORBIT FASTAPI 서버",
    version="0.1.0"
)

app.include_router(active.router)


@app.get("/")
def root():
    return {
        "message": "ORBIT FastAPI server is running"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "server": "fastapi"
    }