from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# own imports
from schemas import Code, GraphState
from prompts.prompts import CODE_GENERATOR_AGENT_PROMPT, CODE_FIXER_AGENT_PROMPT


def code_generator_agent(state: GraphState, llm) -> GraphState:
    print("\n**CODE GENERATOR AGENT**")
    print(state)
    # structured_llm  = llm.with_structured_output(Code, method="json_mode")
    structured_llm = llm.with_structured_output(Code)

    # Format the prompt with the requirement
    # requirement = "Generate Fibonacci series as JSON with `description` and `code` keys"
    requirement = "Hello world program in python, make error there so program will fail"
    prompt = CODE_GENERATOR_AGENT_PROMPT.format(requirement=requirement)

    # Invoke the coder with the formatted prompt
    generated_code = structured_llm.invoke(prompt)
    print("Generated code:", generated_code)

    # Update the state with the generated code
    state["code"] = generated_code
    state["messages"] += [
        AIMessage(content=f"{generated_code.description} \n {generated_code.code}")
    ]

    return state


def write_code_to_file_agent(state: GraphState, code_file):
    print("\n**WRITE CODE TO FILE**")
    print(state)
    with open(code_file, "w") as f:
        f.write(state["code"].code)


def execute_code_agent(state: GraphState, code_file):
    print("\n**EXECUTE CODE**")
    print(state)
    # os.system(f"python {code_file}")
    error = None
    try:
        exec(open(code_file).read())
        print("Code Execution Successful")
    except Exception as e:
        print("Found Error While Running")
        error = f"Execution Error : {e}"
    return {"error": error}


def debug_code_agent(state: GraphState, llm):
    print("\n **DEBUG CODE**")
    print(state)
    error = state["error"]
    code = state["code"].code
    structured_llm = llm.with_structured_output(Code)
    prompt = CODE_FIXER_AGENT_PROMPT.format(original_code=code, error_message=error)
    generated_code = structured_llm.invoke(prompt)
    print("Generated code:", generated_code)

    # Update the state with the generated code
    state["code"] = generated_code
    state["messages"] += [
        AIMessage(content=f"{generated_code.description} \n {generated_code.code}")
    ]
    state["iterations"] += 1

    return state
