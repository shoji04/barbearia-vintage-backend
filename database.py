"""
Modelo do banco de dados - Sistema Barbearia Vintage
Usa SQLAlchemy com SQLite (um arquivo local, sem precisar instalar servidor de banco)
"""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class Funcionario(db.Model):
    """Usuário que acessa o sistema (login)"""
    __tablename__ = "funcionarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    senha_hash = db.Column(db.String(200), nullable=False)  # nunca salvar senha em texto puro

    def __repr__(self):
        return f"<Funcionario {self.email}>"


class Cliente(db.Model):
    """Cliente da barbearia"""
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    observacoes = db.Column(db.Text, nullable=True)  # ex: "prefere corte baixo", "alérgico a produto X"

    # Um cliente pode ter vários agendamentos
    agendamentos = db.relationship("Agendamento", backref="cliente", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "email": self.email,
            "observacoes": self.observacoes,
        }

    def __repr__(self):
        return f"<Cliente {self.nome}>"


class Agendamento(db.Model):
    """Um horário marcado para um cliente"""
    __tablename__ = "agendamentos"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clientes.id"), nullable=False)

    data = db.Column(db.Date, nullable=False)          # ex: 2026-08-25
    horario = db.Column(db.Time, nullable=False)        # ex: 14:30
    servico = db.Column(db.String(100), nullable=False)  # ex: "Corte", "Corte + Barba", "Barba"

    # Status possíveis: agendado, concluido, cancelado, nao_compareceu
    status = db.Column(db.String(20), nullable=False, default="agendado")

    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "cliente_nome": self.cliente.nome if self.cliente else None,
            "data": self.data.isoformat() if self.data else None,
            "horario": self.horario.strftime("%H:%M") if self.horario else None,
            "servico": self.servico,
            "status": self.status,
        }

    def __repr__(self):
        return f"<Agendamento {self.cliente_id} - {self.data} {self.horario}>"
