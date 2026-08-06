from fastapi import FastAPI

from ello.database import Base, atualizar_estrutura_do_banco, engine
from ello.routes.alunos import router as alunos_router
from ello.routes.livros import router as livros_router

app = FastAPI()

Base.metadata.create_all(engine)
atualizar_estrutura_do_banco()

app.include_router(alunos_router)
app.include_router(livros_router)


@app.get("/alive")
def health():
    return {"status": "yes"}
