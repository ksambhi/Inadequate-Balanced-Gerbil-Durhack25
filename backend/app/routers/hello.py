from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Hello

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/hello")
async def hello():
    """Simple Hello World endpoint returning JSON."""
    return {"message": "hello world"}


@router.post("/hello")
async def create_hello(order: str, db: AsyncSession = Depends(get_db)):
    """Create a new Hello record with the given order string."""
    hello = Hello(order=order)
    db.add(hello)
    await db.commit()
    await db.refresh(hello)
    return {"id": hello.id, "order": hello.order}


@router.get("/hellos")
async def get_hellos(db: AsyncSession = Depends(get_db)):
    """Get all Hello records from the database."""
    result = await db.execute(select(Hello))
    hellos = result.scalars().all()
    return [{"id": h.id, "order": h.order} for h in hellos]


@router.get("/hello/{hello_id}")
async def get_hello(hello_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific Hello record by ID."""
    result = await db.execute(select(Hello).where(Hello.id == hello_id))
    hello = result.scalar_one_or_none()
    if hello is None:
        return {"error": "Hello not found"}, 404
    return {"id": hello.id, "order": hello.order}
