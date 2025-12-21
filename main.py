from agente import responder_usuario

print("Digite sua pergunta (ou 'sair' para encerrar):")

while True:
    mensagem = input("\nVocê: ")
    if mensagem.lower() in ['sair', 'encerrar']:
        break
    try: 
        response = responder_usuario(mensagem, thread_id="usuario_teste")
        print("Agente:", response)
    except Exception as e:
        print(f"Erro ao processar: {e}")
        break
