"""
Roda esse script UMA VEZ pra criar o funcionário que vai fazer login no sistema.
Uso: python seed_funcionario.py
"""

from werkzeug.security import generate_password_hash
from app import app
from database import db, Funcionario

with app.app_context():
    email = input("Email do funcionário: ")
    nome = input("Nome do funcionário: ")
    senha = input("Senha: ")

    if Funcionario.query.filter_by(email=email).first():
        print("Já existe um funcionário com esse email.")
    else:
        funcionario = Funcionario(
            nome=nome,
            email=email,
            senha_hash=generate_password_hash(senha),
        )
        db.session.add(funcionario)
        db.session.commit()
        print(f"Funcionário {nome} criado com sucesso!")
