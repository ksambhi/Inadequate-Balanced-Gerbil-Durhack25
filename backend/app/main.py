from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.hello import router as hello_router
from app.routers.events import router as events_router

app = FastAPI()

# CORS: allow all origins, methods, and headers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(hello_router)
app.include_router(events_router)


# Optional: simple root to indicate service is up
@app.get("/")
async def root():
    return {"status": "ok"}
