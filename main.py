import os
import chainlit as cl
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.pregel import GraphRecursionError

# own imports
from llm_models.openai_models import get_openai_llm
from agents import (
    code_generator_agent,
    write_code_to_file_agent,
    execute_code_agent,
    debug_code_agent,
    read_me_agent,
    dockerizer_agent,
    execute_docker_agent,
)
from schemas import GraphState

load_dotenv()
llm = get_openai_llm()


# Streamlit when starting the chat
@cl.on_chat_start
async def on_chat_start():
    await cl.Message(
        content="Lets generate some code! What kind of program you are planning?"
    ).send()


# Define the paths.
search_path = os.path.join(os.getcwd(), "generated")
code_file = os.path.join(search_path, "src/")
test_file = os.path.join(search_path, "test/test_program.py")

# Create the folders and files if necessary.
if not os.path.exists(search_path):
    os.mkdir(search_path)
    os.mkdir(os.path.join(search_path, "src"))
    os.mkdir(os.path.join(search_path, "test"))


# Create the graph.
workflow = StateGraph(GraphState)


# generate code from user input
async def create_code_f(state: GraphState):
    return await code_generator_agent(state, llm)


# save generated code to file
def write_code_to_file_f(state: GraphState):
    return write_code_to_file_agent(state, code_file)


# execute code from folder
async def execute_code_f(state: GraphState):
    return await execute_code_agent(state, code_file)


# execute docker from folder
async def execute_docker_f(state: GraphState):
    return await execute_docker_agent(state, code_file)


# debug codes if error occurs
async def debug_code_f(state: GraphState):
    return await debug_code_agent(state, llm)


# create readme and developer files
async def read_me_f(state: GraphState):
    return await read_me_agent(state, llm, code_file)


# generate dockerfile and docker-compose file
# TODO:: start docker etc.
async def dockerize_f(state: GraphState):
    return await dockerizer_agent(state, llm, code_file)


# detirmine if we should end (success) or debug (error)
def decide_to_end(state: GraphState):
    print(f"Entering in Decide to End")
    print(f"iterations: {state['iterations']}")
    print(f"error: {state['error']}")
    if state["error"]:
        if state["iterations"] > 2:
            print("\n\n\nToo many iterations!!!!!!!!!\n\n\n")
            return "end"
        return "debugger"
    else:
        return "readme"


# Add the node to the graph.
# image from graph flow is saved in images/graphs/graph_flow.png
workflow.add_node("programmer", create_code_f)
workflow.add_node("saver", write_code_to_file_f)
workflow.add_node("dockerizer", dockerize_f)
#workflow.add_node("executer", execute_code_f) <- replaced with execute_docker_f
workflow.add_node("executer_docker", execute_docker_f)
workflow.add_node("debugger", debug_code_f)
workflow.add_node("readme", read_me_f)

# add the edge to the graph
workflow.add_edge("programmer", "saver")
workflow.add_edge("saver", "dockerizer")
#workflow.add_edge("dockerizer", "executer")
workflow.add_edge("dockerizer", "executer_docker")
workflow.add_edge("debugger", "saver")
workflow.add_edge("readme", END)
workflow.add_conditional_edges(
    source="executer_docker",
    #source="executer",
    path=decide_to_end,
    path_map={
        "readme": "readme",  # If `decide_to_end` returns "end", transition to END
        "debugger": "debugger",  # If `decide_to_end` returns "debugger", transition to the debugger node
    },
)


# set start node
workflow.set_entry_point("programmer")

# Create the app and run it
app = workflow.compile()
# create the image of the graph
app.get_graph().draw_mermaid_png(output_file_path="images/graphs/graph_flow.png")


@cl.on_message  # this function will be called every time a user inputs a message in the UI
async def main(message: cl.Message):
    print(message.content)
    # amount of steps to run (node -> step), so no infinite loop will be created by accident
    # TODO: use iterations instread of steps??
    config = RunnableConfig(recursion_limit=10)
    # first invoke should have something to add to the state

    try:
        results = await app.ainvoke(
            {
                "messages": [
                    HumanMessage(
                        content=message.content
                        # content="Simple website about bengal cats with html, css and javascript files. If images used, use some placeholder images."
                        # content="simple C# hello world program, prints hello word"
                        # content="simple NODEJS hello world program, prints hello word"
                        # content="simple python hello world program, prints hello world"
                        # content="complicated Nodejs hello world program"
                        # content="Python hello world program, print 'Hello, World!' to the console, make error in the code"
                    )
                ],
                "iterations": 0,
            },
            config=config,
        )
    except GraphRecursionError as e:
        print(f"GraphRecursionError: {e}")
    print("nRESULT:")
    print(results)

    await cl.Message(content="done!").send()
