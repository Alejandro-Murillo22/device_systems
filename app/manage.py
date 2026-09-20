"""Administración local de credenciales: python -m app.manage --help."""
import argparse
from getpass import getpass

from pydantic import EmailStr, TypeAdapter
from sqlalchemy import func, select

from app.database.database import SessionLocal
from app.models import User
from app.security import hash_password


def main():
    parser = argparse.ArgumentParser(description="Administración local; las contraseñas se solicitan sin eco")
    parser.add_argument("command", choices=["create-admin", "set-password"])
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", default="Administrador")
    args = parser.parse_args()
    try:
        email = str(TypeAdapter(EmailStr).validate_python(args.email)).lower()
        name = args.name.strip()
        if not 3 <= len(name) <= 80:
            raise ValueError("El nombre debe tener de 3 a 80 caracteres")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(func.lower(User.email) == email))
            if args.command == "create-admin" and user is not None:
                raise ValueError("El correo ya existe; no se modifica su rol automáticamente")
            if args.command == "set-password" and user is None:
                raise ValueError("El usuario no existe")
            password = getpass("Contraseña: ")
            if password != getpass("Repetir contraseña: "):
                raise ValueError("Las contraseñas no coinciden")
            hashed = hash_password(password)
            if args.command == "create-admin":
                user = User(name=name, email=email, role="admin", is_active=True)
                db.add(user)
            user.hashed_password = hashed
            db.commit()
        print("Credenciales guardadas correctamente.")
    except ValueError as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    main()
