import ollama
import json
import re #regex
from db import consultar_viagem

SYSTEM_PROMPT = """
Você é uma assistente de uma empresa de transporte e turismo chamada Rota-Fácil que atende a região Norte e Nordeste do Brasil.
Sua função é entender pedidos de passagens e identificar:
- cidade de origem
- cidade de destino
- data da viagem

Se o usuário não estiver falando sobre viagem, apenas responda de forma educada e natural, como uma assistente amigável.
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
    # print("Resposta bruta (entidades)", content)

    # Captura o JSON (tudo que estiver entre {})
    match = re.search(r"\{.*\}", content, re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group())
        return data
    except Exception:
        print("Erro ao decodificar JSON.")
        return None


def responder_usuario(mensagem):
    dados = extrair_detalhes(mensagem)

    # Se o modelo não retornou nada que pareça ser viagem
    if not dados or not any([dados.get("origem"), dados.get("destino"), dados.get("data")]):
        # Responder livremente
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": mensagem}
            ]
        )
        return response["message"]["content"]

    # Conseguiu extrair os dados da viagem
    origem = dados.get("origem")
    destino = dados.get("destino")
    data = dados.get("data")

    viagem = consultar_viagem(origem, destino, data)

    if viagem:
        vagas = viagem["vagas"]
        if vagas > 0:
            return f"Sim! Temos {vagas} vaga(s) disponível(is) de {origem} para {destino} no dia {data}."
        else:
            return f"Infelizmente não temos mais vagas de {origem} para {destino} no dia {data}."
    else:
        return f"Não encontrei viagens de {origem} para {destino} no dia {data}."
