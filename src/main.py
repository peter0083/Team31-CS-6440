"""
Sample FastAPI Application
"""
from fastapi import FastAPI

app = FastAPI(title="Sample API", version="0.1.0")


def get_app() -> FastAPI:
    return app
@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Hello World"}
