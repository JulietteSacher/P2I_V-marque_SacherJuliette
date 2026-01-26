from fastapi import FastAPI

from app.core.database import Base, engine
import app.models  # force l'import du package models

Base.metadata.create_all(bind=engine)

from app.api.routes.health import router as health_router
from app.api.routes.teams import router as teams_router
from app.api.routes.players import router as players_router


app = FastAPI(title="V-Marque API", version="0.1.0")
app.include_router(health_router)
app.include_router(teams_router)
app.include_router(players_router)

@app.get("/")
def root():
    return {"name": "V-Marque API", "status": "ok"}
