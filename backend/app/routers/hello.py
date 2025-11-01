from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/hello")
async def hello():
    """Simple Hello World endpoint returning JSON."""
    return {"message": "hello world"}
