import ollama
import json
import re #regex
from datetime import datetime
from db import consultar_viagem


SYSTEM_PROMPT = """
Você é uma assistente de uma empresa de transporte e turismo.
Sua função é entender pedidos de passagens e identificar:
- cidade de origem
- cidade de destino
- data da viagem

Responda sempre de forma educada e útil.
"""

def extrair_detalhes(texto):
    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Extraia origem, destino e data da frase: '{texto}' e responda no formato JSON."}
        ]
    )

    content = response["message"]["content"]
    print("Resposta bruta (entidades)", content)

    #Captura o JSON (tudo que estiver entre {})
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        return data
    except Exception:
        print("Error", Exception)
        return None

def responder_usuario(mensagem):
    dados = extrair_detalhes(mensagem)

    if not dados:
        return "Desculpe, não consegui entender os detalhes da viagem. Pode repetir a pergunta ?"

    origem = dados.get("origem")
    destino = dados.get("destino")
    data = dados.get("data")

    viagem = consultar_viagem(origem, destino, data)
    print("Viagens consulta", viagem)
    if viagem:
        vagas = viagem["vagas"]
        if vagas >0:
            return f"Sim, Temos {vagas} vagas disponiveis de {origem} para {destino} no dia {data}"
        else:
            return f"Infelizmente não temos mais vagas de {origem} para {destino} no dia {data}."
    else: #Isso aqui vai ser mais extenso
        return f"Não encontrei viagens de {origem} para {destino} no dia {data}."