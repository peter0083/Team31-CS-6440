"""
Sample FastAPI Application
"""
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="Sample API", version="0.1.0")


class Item(BaseModel):
    name: str
    description: str | None = None
    price: float
    tax: float | None = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Hello World"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/items/")
async def create_item(item: Item):
    """Create an item"""
    return {"item": item, "message": "Item created successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
