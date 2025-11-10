from agente import responder_usuario
print("Digite sua pergunta (ou 'sair', 'encerrar' para encerrar):")

while True:
    mensagem = input("Voce: ")
    if mensagem.lower() in ["sair", "encerrar"]:
        break
    resposta = responder_usuario(mensagem)
    print("ROta fácil :", resposta)