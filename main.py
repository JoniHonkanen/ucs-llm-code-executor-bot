import os
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
)
from schemas import GraphState

load_dotenv()
llm = get_openai_llm()

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
def create_code_f(state: GraphState):
    return code_generator_agent(state, llm)


# save generated code to file
def write_code_to_file_f(state: GraphState):
    return write_code_to_file_agent(state, code_file)


# execute code from folder
def execute_code_f(state: GraphState):
    return execute_code_agent(state, code_file)


# debug codes if error occurs
def debug_code_f(state: GraphState):
    return debug_code_agent(state, llm)


# detirmine if we should end (success) or debug (error)
def decide_to_end(state: GraphState):
    print(f"Entering in Decide to End")
    print(f"iterations: {state['iterations']}")
    if state["error"]:
        if state["iterations"] > 0:
            print("\n\n\nToo many iterations!!!!!!!!!\n\n\n")
            return "end"
        return "debugger"
    else:
        return "end"


# Add the node to the graph.
# image from graph flow is saved in images/graphs/graph_flow.png
workflow.add_node("programmer", create_code_f)
workflow.add_node("saver", write_code_to_file_f)
workflow.add_node("executer", execute_code_f)
workflow.add_node("debugger", debug_code_f)

# add the edge to the graph
workflow.add_edge("programmer", "saver")
workflow.add_edge("saver", "executer")
workflow.add_edge("debugger", "saver")
workflow.add_conditional_edges(
    source="executer",
    path=decide_to_end,
    path_map={
        "end": END,  # If `decide_to_end` returns "end", transition to END
        "debugger": "debugger",  # If `decide_to_end` returns "debugger", transition to the debugger node
    },
)


# set start node
workflow.set_entry_point("programmer")

# Create the app and run it
app = workflow.compile()
# create the image of the graph
app.get_graph().draw_mermaid_png(output_file_path="images/graphs/graph_flow.png")

# amount of steps to run (node -> step), so no infinite loop will be created by accident
# TODO: use iterations instread of steps??
config = RunnableConfig(recursion_limit=10)
# first invoke should have something to add to the state
try:
    results = app.invoke(
        {
            "messages": [
                HumanMessage(
                    # content="Simple website about bengal cats with html, css and javascript files. If images used, use some placeholder images."
                    # content="Create hello world program with intentional error"
                    # content="complicated Nodejs hello world program"
                    content="Python hello world program, print 'Hello, World!' to the console, make error in the code"
                )
            ],
            "iterations": 0,
        },
        config=config,
    )
except GraphRecursionError as e:
    print(f"GraphRecursionError: {e}")
