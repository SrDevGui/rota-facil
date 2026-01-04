from langchain.tools import tool
from langchain.chat_models import init_chat_model
from rich import print
import re, json
from langchain.messages import AnyMessage
from typing_extensions import TypedDict, List, Annotated
import operator
from langchain.messages import SystemMessage
from langchain.messages import ToolMessage
from langchain.messages import HumanMessage
from typing import Literal
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages # Importante para o histórico
from langgraph.checkpoint.memory import MemorySaver
from db import consultar_viagem

model = init_chat_model(
    "ollama:llama3.2",
    temperature=0
)

# 1 Define tools and modelíí
@tool
def extract_entites(text: str) ->dict:
    """ Extrair origem, destino e data da mensagem  
    
    Args:í
        text: str : mensagem do usuario
    """
    prompt = f"""
     Extraia as entidades (origem, destino e data) da frase abaixo.
     Frase: "{text}"
     responda em JSON.
    """
    resp = model.invoke(prompt).content

    # print(f"Prompt 0: {model.invoke(prompt)}")
    print("resp", resp)

    match = re.search(r"\{.*\}", resp, re.DOTALL) #formata re
    print("Match", match)

    return json.loads(match.group()) if match else {"erro": "não foi possível extrair as entidades"}

@tool
def make_query(entidades: dict = None, origem: str = None, destino: str = None, data: str = None) -> dict:
    """Simula uma consulta a uma base de dados de viagens de onibus.
    Aceita um dicionário `entidades` ou os parâmetros nomeados `origem`, `destino`, `data`.
    """
    # Normalizar entrada: aceitar tanto {'entidades': {...}} quanto {...} ou parâmetros nomeados
    print("Entidades/args recebidos no make_query:", entidades, origem, destino, data)

    if entidades is None:
        # se entidades não foi fornecido, montar a partir dos kwargs
        entidades = {}
        if origem is not None:
            entidades["origem"] = origem
        if destino is not None:
            entidades["destino"] = destino
        if data is not None:
            entidades["data"] = data

    # Caso a chamada passada diretamente o dict com as chaves (origem,destino,data)
    if isinstance(entidades, dict) and any(k in entidades for k in ("origem", "destino", "data")):
        origem = entidades.get("origem")
        destino = entidades.get("destino")
        data = entidades.get("data")
    else:
        # Se o LLM passou o dict diretamente sem chave 'entidades', ele pode chegar aqui
        try:
            # tentar extrair do primeiro valor se for um dict aninhado
            if isinstance(entidades, dict) and len(entidades) == 1:
                first = next(iter(entidades.values()))
                if isinstance(first, dict):
                    origem = first.get("origem")  
                    destino = first.get("destino")
                    data = first.get("data")
        except Exception:
            pass

    print(f"entidades normalizadas:", origem, destino, data)

    if not origem or not destino or not data:
        return {"error": "Dados insuficientes para consulta"}

    viagem = consultar_viagem(origem, destino, data)

    if not viagem:
        return {"vagas": 0, "message": f"Não encontrei viagens de {origem} para {destino} no dia {data}"}

    vagas = viagem.get("vagas", 0)
    print(f"Vagas encontradas: {vagas}")
    # return {"vagas": vagas, "origem": origem, "destino": destino, "data": data}
    return {"vagas": vagas}
    # if vagas > 0:
    #     return f"Temos {vagas} vaga(s) de origem para {destino} no dia {data}."
    # else:
    #     return f"Não há vagas disponíveis para essa viagem."

#Augment (aumentar) the LLM with tools
tools = [extract_entites, make_query]
tools_by_name = {tool.name: tool for tool in tools}
model_with_tools = model.bind_tools(tools)

# 2 Define State
class MessageState(TypedDict):
    messages: Annotated[List[AnyMessage], add_messages] #Essa variavel é uma lista, mas quando receber novos dados 
    #use a funcao 'add_messages' para adicionar ao historico (append)

# 3 Define model node
def llm_call(state: MessageState):
    sys_msg = SystemMessage(content = """ Você é um assistente que ajuda a encontrar vagas de viagem de ônibus entre cidades brasileiras. 
    Utilize as ferramentas disponíveis para extrair informações da mensagem do usuário. 
    Responda de forma clara e objetiva. Caso a mensagem do usuário não esteja relacionada a viagens de ônibus, responda de maneira normal.""")
    #Invocar o modelo passando a mensagem de sistem + o histórico
    response = model_with_tools.invoke([sys_msg] + state["messages"])
    return {"messages":[response]}

# 4 Define tool node 
def tool_node(state: MessageState):
    print("States no tool node:", state)
    result = []
    last_message = state["messages"][-1] #AIMessage
    for tool_call in getattr(last_message, "tool_calls", []):
        tool_obj = tools_by_name[tool_call["name"]] # Aqui ele vai chamar as tools pelos nomes
        args = tool_call.get("args", None)
        print(f"Args : {args}, args length {len(args)}")
        # Se args for um dict com único campo, use o valor; caso contrário passe direto
        # if isinstance(args, dict) and len(args) == 1: #Pega no segundo loop
        if isinstance(args, dict) and len(args) == 1: #Pega no segundo loop, esse 1 é inutil
            single_arg = next(iter(args.values()))
            print(f"Single arg: {single_arg}")
            observation = tool_obj.invoke(single_arg)
            print(f"Observation single arg: {observation}")
        else:
            observation = tool_obj.invoke(args)

        # Garantir conteúdo serializável e associar o nome do tool_call
        try:
            content = json.dumps(observation)
            print(f"Content tool node: {content}")
        except Exception:
            content = str(observation)

        result.append(ToolMessage(content=content, tool_call_id=tool_call["id"], tool=tool_call["name"]))
        print(f"Tool message appended: {result}")
    return {"messages": result}

# 5 Define end logic
# The conditional edge function is used to route to the tool node or end based upon
# whether the LLM made a tool call
def should_continue(state: MessageState) -> Literal["tool_node", "__end__"]:
    last_message = state["messages"][-1]

    # Some message objects may not have `tool_calls`; guard with hasattr
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tool_node"

    # Otherwise, we stop (reply to the user)
    return "__end__"

# 6 Build and compile the agent
#Build workflow
agent_builder = StateGraph(MessageState)

#Adding nodes
agent_builder.add_node("llm_call", llm_call)
agent_builder.add_node("tool_node", tool_node)


#Definindo bordas (edges)
agent_builder.add_edge(START, "llm_call")
agent_builder.add_conditional_edges("llm_call", should_continue)
agent_builder.add_edge("tool_node", "llm_call")

#Complile the agent
agent = agent_builder.compile()
#Memory (checkpoint)
memory = MemorySaver()
agent = agent_builder.compile(checkpointer=memory)

#Invoke
def responder_usuario(user_input:str, thread_id: str = "1"):
    config = {"configurable": {"thread_id": thread_id}}

    state = {
        "messages":[
            HumanMessage(content=user_input)
        ]
    }
    result = agent.invoke(state, config=config)
    return result["messages"][-1].content