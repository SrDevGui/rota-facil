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


model = init_chat_model(
    "ollama:llama3.2",
    temperature=0
)

# 1 Define tools and model
@tool
def extract_entites(text: str) ->dict:
    """ Extrair origem, destino e data da mensagem  
    
    Args:
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

#Augment (aumentar) the LLM with tools
tools = [extract_entites]
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
    """ 
        Performs the tool call
    """
    result = []
    last_message = state["messages"][-1]
    for tool_call in last_message.tool_calls:
        tool_obj = tools_by_name[tool_call["name"]]
        observation = tool_obj.invoke(tool_call["args"])
        result.append(ToolMessage(content=json.dumps(observation), tool_call_id=tool_call["id"]))
    return {"messages":result}

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