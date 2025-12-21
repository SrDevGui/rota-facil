from langchain_ollama import ChatOllama
from langchain.tools import tool
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import re, json
from db import consultar_viagem
from rich import print


#State agent
class State(TypedDict):
    messages: List[dict]
    entities: dict
    resposta: str

#LLM
llm = ChatOllama(model = "llama3.2")

#Tool 1 : extrair entidades
@tool
def extrair_entidades(texto: str) -> dict:
    """ Extrair origem, destino e data da mensagem  """
    prompt = f"""
    extraia as entidades (origem, destino e data) da frase abaixo.
    Frases: "{texto}"
    Responda somente JSOM.
    """

    resp = llm.invoke(prompt).content
    print(f"Prompt 0: {llm.invoke(prompt)}")
    print("resp", resp)

    match = re.search(r"\{.*\}", resp, re.DOTALL) #formata re
    print("Match", match)
    if not match:
        return {}

    try: 
        return json.loads(match.group())
    except:
        return {}

@tool
def consultar_db(entities: dict) ->str:
    """Consulta viagem no banco."""
    origem = entidades.get("origem")
    destino = entidades.get("destino")
    data = entidades.get("data")
    print(f"entidades", origem, destino, data)

    if not origem or not destino or not data:
        return "Não encontrei dados suficientes de viagem."
    
    viagem = consultar_viagem(origem, destino, data)

    if not viagem:
        return f"Não encontrei viagens de {origem} para {destino} no dia {data}"
    
    vagas = viagem["vagas"]

    if vagas > 0:
        return f"Temos {vagas} vaga(s) de origem para {destino} no dia {data}."
    else:
        return f"Não há vagas disponíveis para essa viagem."

#Nó intepreta mensagem
def interpretar(state: State):
    user_msg = state["messages"][-1]["content"]

    # Tenta extrair entidades
    entidades = extrair_entidades.run(user_msg)
    state["entities"] = entidades
    print("Entidades", entidades)

    return state


# Nó: Decidir ação
def decidir(state: State):
    if state["entities"].get("origem") or state["entities"].get("destino"):
        resposta = consultar_db.run(state["entities"])
        state["resposta"] = resposta
    else:
        #Resposta livre
        resposta = llm.invoke(state["messages"]).content
        state["resposta"] = resposta

    return state

#Construção  
workflow = StateGraph(State)
workflow.add_node("interpretar", interpretar)
workflow.add_node("decidir", decidir)

workflow.set_entry_point("interpretar")
workflow.add_edge("interpretar", "decidir")
workflow.add_edge("decidir", END)

agent = workflow.compile()
agent.get_graph().draw_mermaid_png(output_file_path = 'file.png')