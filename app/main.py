from fastapi import FastAPI
from app.api.routes.health import router as health_router

app = FastAPI(title="V-Marque API", version="0.1.0")

app.include_router(health_router)

@app.get("/")
def root():
    return {"name": "V-Marque API", "status": "ok"}


from app.core.database import Base, engine
from app import models  # force l'import des modèles quand tu en auras

Base.metadata.create_all(bind=engine)
