import os
from dotenv import load_dotenv
from typing import TypedDict, List
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langgraph.pregel import GraphRecursionError

# own imports
from prompts.prompts import CODE_GENERATOR_AGENT, CODE_FIXER_AGENT

load_dotenv()
llm = ChatOpenAI(model="gpt-4o-mini")

# Define the paths.
search_path = os.path.join(os.getcwd(), "generated")
code_file = os.path.join(search_path, "src/crud.py")
test_file = os.path.join(search_path, "test/test_crud.py")

# Create the folders and files if necessary.
if not os.path.exists(search_path):
    os.mkdir(search_path)
    os.mkdir(os.path.join(search_path, "src"))
    os.mkdir(os.path.join(search_path, "test"))


class Code(BaseModel):
    """Plan to follow in future"""

    description: str = Field(description="Detailed description of the code generated")
    code: str = Field(description="Python code generated based on the requirements")


#class CodeFix(BaseModel):
#    """Schema to capture the process of fixing code."""
#
#    fixed_code: str = Field(
#        description="The corrected Python code after fixing the errors."
#    )
#    description: str = Field(
#        description="Detailed description of the changes made to fix the code."
#    )
#    suggestions: str = Field(
#        description="Additional suggestions or improvements made to the original code, if any.",
#        default="",
#    )


class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        code : Code solution
        iterations : Number of tries
    """

    error: str
    messages: List
    code: str
    iterations: int


# Create the graph.
workflow = StateGraph(GraphState)


# function for discover agent, which generate the code and save it to the files, also add the state to the graph
def discover_function(state: GraphState) -> GraphState:
    print("\n**DISCOVER FUNCTION**")
    print("Executing discover_function with state:", state)
    # Using the with_structured_output method
    # structured_llm  = llm.with_structured_output(Code, method="json_mode")
    structured_llm = llm.with_structured_output(Code)

    # Format the prompt with the requirement
    # requirement = "Generate Fibonacci series as JSON with `description` and `code` keys"
    requirement = "Hello world program in python, make error there so program will fail"
    prompt = CODE_GENERATOR_AGENT.format(requirement=requirement)

    # Invoke the coder with the formatted prompt
    generated_code = structured_llm.invoke(prompt)
    print("Generated code:", generated_code)

    # Update the state with the generated code
    state["code"] = generated_code
    state["messages"] += [
        AIMessage(content=f"{generated_code.description} \n {generated_code.code}")
    ]

    return state


# write code to a executable file
def write_code_to_file(state: GraphState):
    print("\n**WRITE CODE TO FILE**")
    print(state)
    with open(code_file, "w") as f:
        f.write(state["code"].code)


def execute_code(state: GraphState):
    print("\n**EXECUTE CODE**")
    # os.system(f"python {code_file}")
    error = None
    try:
        exec(open(code_file).read())
        print("Code Execution Successful")
    except Exception as e:
        print("Found Error While Running")
        error = f"Execution Error : {e}"
    print(state)
    return {"error": error}


# Takes orginal code & error message, and try to improve it
def debug_code(state: GraphState):
    print("\n **DEBUG CODE**")
    print(state)
    error = state["error"]
    code = state["code"].code
    structured_llm = llm.with_structured_output(Code)
    prompt = CODE_FIXER_AGENT.format(original_code=code, error_message=error)
    generated_code = structured_llm.invoke(prompt)
    print("Generated code:", generated_code)

    # Update the state with the generated code
    state["code"] = generated_code
    state["messages"] += [
        AIMessage(
            content=f"{generated_code.description} \n {generated_code.code}"
        )
    ]
    state["iterations"] += 1

    return state


def decide_to_end(state):
    print(f"Entering in Decide to End")
    if state["error"]:
        return "debugger"
    else:
        return "end"


# Add the node to the graph.
workflow.add_node("programmer", discover_function)
workflow.add_node("saver", write_code_to_file)
workflow.add_node("executer", execute_code)
workflow.add_node("debugger", debug_code)

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
app.get_graph().draw_mermaid_png(output_file_path="images/graphs/chainlit_graph.png")

# amount of steps to run (node -> step), so no infinite loop will be created by accident
config = RunnableConfig(recursion_limit=10)
# first invoke should have something to add to the state
try:
    results = app.invoke(
        {
            "messages": [HumanMessage(content="Hello world program with python")],
            "iterations": 0,
        },
        config=config,
    )
except GraphRecursionError as e:
    print(f"GraphRecursionError: {e}")
