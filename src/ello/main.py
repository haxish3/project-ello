from fastapi import FastAPI

from ello.database import Base, engine
from ello.routes.alunos import router as alunos_router

app = FastAPI()

Base.metadata.create_all(engine)

app.include_router(alunos_router)


@app.get("/alive")
def health():
    return {"status": "yes"}
