import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ello.config import FRONTEND_ORIGINS, PORT
from ello.routes.alunos import router as alunos_router
from ello.routes.auth import router as auth_router
from ello.routes.dev import router as dev_router
from ello.routes.livros import router as livros_router
from ello.routes.usuarios import router as usuarios_router

app = FastAPI(title="Ello - Gestão Escolar", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(alunos_router)
app.include_router(livros_router)
app.include_router(auth_router)
app.include_router(usuarios_router)
app.include_router(dev_router)


@app.get("/alive")
def health():
    return {"status": "ok"}


def run():
    uvicorn.run("ello.main:app", host="127.0.0.1", port=8000, reload=True)


def run_production():
    uvicorn.run("ello.main:app", host="0.0.0.0", port=PORT, proxy_headers=True)
