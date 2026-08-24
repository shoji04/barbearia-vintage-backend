"""
API principal - Sistema Barbearia Vintage
Rotas: login, CRUD de clientes, CRUD de agendamentos
Ao criar um agendamento, dispara um webhook pro n8n mandar e-mail ao cliente
"""

import os
from datetime import datetime, date, time

import requests
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager, create_access_token, jwt_required, get_jwt_identity
)
from werkzeug.security import check_password_hash
from sqlalchemy.exc import IntegrityError

from database import db, Cliente, Agendamento, Funcionario

app = Flask(__name__)

# --- Configurações ---
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///barbearia.db"
app.config["JWT_SECRET_KEY"] = os.environ.get("JWT_SECRET_KEY", "troque-essa-chave-no-env")

N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/novo-agendamento")

db.init_app(app)
jwt = JWTManager(app)
CORS(app)  # permite o frontend (rodando em outra porta/arquivo) chamar essa API

with app.app_context():
    db.create_all()


# ==================== LOGIN ====================

@app.route("/login", methods=["POST"])
def login():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição deve ser um JSON válido"}), 400

    email = dados.get("email")
    senha = dados.get("senha")

    funcionario = Funcionario.query.filter_by(email=email).first()

    if not funcionario or not check_password_hash(funcionario.senha_hash, senha):
        return jsonify({"erro": "Email ou senha inválidos"}), 401

    token = create_access_token(identity=str(funcionario.id))
    return jsonify({"token": token, "nome": funcionario.nome}), 200


# ==================== CLIENTES (CRUD) ====================

@app.route("/clientes", methods=["GET"])
@jwt_required()
def listar_clientes():
    clientes = Cliente.query.all()
    return jsonify([c.to_dict() for c in clientes]), 200


@app.route("/clientes/<int:cliente_id>", methods=["GET"])
@jwt_required()
def obter_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    return jsonify(cliente.to_dict()), 200


@app.route("/clientes", methods=["POST"])
@jwt_required()
def criar_cliente():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição deve ser um JSON válido"}), 400

    if not dados.get("nome") or not dados.get("email"):
        return jsonify({"erro": "nome e email são obrigatórios"}), 400

    cliente = Cliente(
        nome=dados["nome"],
        email=dados["email"],
        observacoes=dados.get("observacoes", ""),
    )
    db.session.add(cliente)
    db.session.commit()
    return jsonify(cliente.to_dict()), 201


@app.route("/clientes/<int:cliente_id>", methods=["PUT"])
@jwt_required()
def editar_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição deve ser um JSON válido"}), 400

    cliente.nome = dados.get("nome", cliente.nome)
    cliente.email = dados.get("email", cliente.email)
    cliente.observacoes = dados.get("observacoes", cliente.observacoes)

    db.session.commit()
    return jsonify(cliente.to_dict()), 200


@app.route("/clientes/<int:cliente_id>", methods=["DELETE"])
@jwt_required()
def remover_cliente(cliente_id):
    cliente = Cliente.query.get_or_404(cliente_id)
    db.session.delete(cliente)
    db.session.commit()
    return jsonify({"mensagem": "Cliente removido"}), 200


# ==================== AGENDAMENTOS (CRUD) ====================

@app.route("/agendamentos", methods=["GET"])
@jwt_required()
def listar_agendamentos():
    # Suporta filtro opcional por data: /agendamentos?data=2026-08-25
    filtro_data = request.args.get("data")

    query = Agendamento.query
    if filtro_data:
        try:
            query = query.filter_by(data=date.fromisoformat(filtro_data))
        except ValueError:
            return jsonify({"erro": "Parâmetro 'data' inválido, use o formato AAAA-MM-DD"}), 400

    agendamentos = query.order_by(Agendamento.data, Agendamento.horario).all()
    return jsonify([a.to_dict() for a in agendamentos]), 200


@app.route("/agendamentos", methods=["POST"])
@jwt_required()
def criar_agendamento():
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição deve ser um JSON válido"}), 400

    obrigatorios = ["cliente_id", "data", "horario", "servico"]
    faltando = [campo for campo in obrigatorios if not dados.get(campo)]
    if faltando:
        return jsonify({"erro": f"Campos obrigatórios faltando: {faltando}"}), 400

    cliente = Cliente.query.get(dados["cliente_id"])
    if not cliente:
        return jsonify({"erro": "Cliente não encontrado"}), 404

    try:
        nova_data = date.fromisoformat(dados["data"])
        novo_horario = time.fromisoformat(dados["horario"])
    except ValueError:
        return jsonify({"erro": "'data' deve ser AAAA-MM-DD e 'horario' deve ser HH:MM"}), 400

    # Evita marcar dois agendamentos no mesmo horário (diferencial que ataca
    # o problema de duplicidade que o Marcelo descreveu no case)
    conflito = Agendamento.query.filter_by(
        data=nova_data, horario=novo_horario
    ).filter(Agendamento.status != "cancelado").first()

    if conflito:
        return jsonify({"erro": "Já existe um agendamento nesse horário"}), 409

    agendamento = Agendamento(
        cliente_id=cliente.id,
        data=nova_data,
        horario=novo_horario,
        servico=dados["servico"],
        status="agendado",
    )
    db.session.add(agendamento)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"erro": "Já existe um agendamento nesse horário"}), 409

    # Dispara o webhook do n8n pra ele mandar o e-mail de confirmação
    try:
        requests.post(N8N_WEBHOOK_URL, json={
            "cliente_nome": cliente.nome,
            "cliente_email": cliente.email,
            "data": agendamento.data.isoformat(),
            "horario": agendamento.horario.strftime("%H:%M"),
            "servico": agendamento.servico,
        }, timeout=5)
    except requests.exceptions.RequestException as e:
        # Não deixa o agendamento falhar só porque o n8n está fora do ar
        print(f"Aviso: falha ao chamar webhook do n8n: {e}")

    return jsonify(agendamento.to_dict()), 201


@app.route("/agendamentos/<int:agendamento_id>", methods=["PUT"])
@jwt_required()
def editar_agendamento(agendamento_id):
    agendamento = Agendamento.query.get_or_404(agendamento_id)
    dados = request.get_json(silent=True)
    if not dados:
        return jsonify({"erro": "Corpo da requisição deve ser um JSON válido"}), 400

    try:
        if "data" in dados:
            agendamento.data = date.fromisoformat(dados["data"])
        if "horario" in dados:
            agendamento.horario = time.fromisoformat(dados["horario"])
    except ValueError:
        return jsonify({"erro": "'data' deve ser AAAA-MM-DD e 'horario' deve ser HH:MM"}), 400

    if "servico" in dados:
        agendamento.servico = dados["servico"]
    if "status" in dados:
        status_validos = ["agendado", "concluido", "cancelado", "nao_compareceu"]
        if dados["status"] not in status_validos:
            return jsonify({"erro": f"status deve ser um de: {status_validos}"}), 400
        agendamento.status = dados["status"]

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"erro": "Já existe um agendamento nesse horário"}), 409

    return jsonify(agendamento.to_dict()), 200


@app.route("/agendamentos/<int:agendamento_id>", methods=["DELETE"])
@jwt_required()
def remover_agendamento(agendamento_id):
    agendamento = Agendamento.query.get_or_404(agendamento_id)
    db.session.delete(agendamento)
    db.session.commit()
    return jsonify({"mensagem": "Agendamento removido"}), 200


if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(debug=debug, port=5001)
