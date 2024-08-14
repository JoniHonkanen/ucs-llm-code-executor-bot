from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import subprocess
import shlex
import os

# own imports
from schemas import Code, Codes, GraphState
from prompts.prompts import CODE_GENERATOR_AGENT_PROMPT, CODE_FIXER_AGENT_PROMPT


def code_generator_agent(state: GraphState, llm) -> GraphState:
    print("\n**CODE GENERATOR AGENT**")
    print(state)
    structured_llm = llm.with_structured_output(Codes)

    # get first message from state
    requirement = state["messages"][0].content
    print("Requirement:", requirement)
    prompt = CODE_GENERATOR_AGENT_PROMPT.format(requirement=requirement)

    # Invoke the coder with the formatted prompt
    generated_code = structured_llm.invoke(prompt)

    print("\nGenerated code:", generated_code)

    # Update the state with the generated code

    state["codes"] = generated_code
    state["messages"] += [
        AIMessage(
            content=f"{generated_code.description} \n {generated_code.codes}"
        )  # TODO: pitääkö generated_code2.codes for loopata codes läpi? varmaan pitää
    ]

    return state


def write_code_to_file_agent(state: GraphState, code_file):
    print("\n**WRITE CODE TO FILE**")
    print(state)

    # loop through the codes and write them to file
    for code in state["codes"].codes:
        if code.executable_code:
            state["executable_file_name"] = code.filename
        formatted_code = code.code.replace("\\n", "\n")
        with open(code_file + code.filename, "w") as f:
            f.write(formatted_code)
    return state


def execute_code_agent(state: GraphState, code_file):
    print("\n**EXECUTE CODE**")
    print(state)

    error = None
    try:
        # Construct the full path to the executable file
        executable_file_path = os.path.join(code_file, state["executable_file_name"])

        # Update the execution command to use the full path
        execution_command = shlex.split(state["codes"].execution_command)

        # Replace the script filename in the command with the full path
        execution_command[1] = executable_file_path
        
        # Execute the command
        result = subprocess.run(execution_command, capture_output=True, text=True)

        if result.returncode != 0:
            error = f"Execution failed with error: {result.stderr}"

    except Exception as e:
        print("Found Error While Running")
        error = f"Execution Error : {e}"
    return {"error": error}


def debug_code_agent(state: GraphState, llm):
    print("\n **DEBUG CODE**")
    print(state)
    error = state["error"]
    code = state["codes"].codes
    print("CODE: ", code)
    structured_llm = llm.with_structured_output(Codes)
    prompt = CODE_FIXER_AGENT_PROMPT.format(original_code=code, error_message=error)
    generated_code = structured_llm.invoke(prompt)
    print("\nNEW FIXED CODE:", generated_code)

    # Update the state with the generated code
    state["codes"] = generated_code
    state["messages"] += [
        AIMessage(content=f"{generated_code.description} \n {generated_code.codes}")
    ]
    state["iterations"] += 1

    return state
