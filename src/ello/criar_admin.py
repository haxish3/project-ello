import getpass

from sqlalchemy import select

from ello.database import SessionLocal
from ello.models import Cargo, Usuario
from ello.routes.auth import gerar_hash


def main():
    nome = input("Nome do administrador: ").strip()
    login = input("Login do administrador: ").strip().casefold()
    senha = getpass.getpass("Senha (mínimo 8 caracteres): ")
    confirmacao = getpass.getpass("Confirme a senha: ")

    if not nome or not login:
        raise SystemExit("Nome e login são obrigatórios.")
    if len(senha) < 8:
        raise SystemExit("A senha precisa ter pelo menos 8 caracteres.")
    if senha != confirmacao:
        raise SystemExit("As senhas não são iguais.")

    with SessionLocal() as banco:
        if banco.scalar(select(Usuario).where(Usuario.login == login)) is not None:
            raise SystemExit("Já existe um usuário com esse login.")

        cargo_admin = banco.scalar(select(Cargo).where(Cargo.nome == "admin"))
        if cargo_admin is None:
            raise SystemExit("Execute 'uv run alembic upgrade head' primeiro.")

        usuario = Usuario(
            nome=nome,
            login=login,
            senha_hash=gerar_hash(senha),
            cargos=[cargo_admin],
        )
        banco.add(usuario)
        banco.commit()
        print(f"Administrador '{login}' criado com sucesso.")


if __name__ == "__main__":
    main()
