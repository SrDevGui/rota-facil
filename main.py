from agente import agent

state = {
    "messages": [
        {"role": "user", "content": "Tem vaga de Goiânia pra Manaus pra data 2025-10-25 ?"}
    ]
}

result = agent.invoke(state)
print(result["resposta"])
