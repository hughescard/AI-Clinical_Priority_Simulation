from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.experiment_routes import router as experiment_router
from app.api.simulation_routes import router as simulation_router
from app.config import settings

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(simulation_router)
app.include_router(experiment_router)
