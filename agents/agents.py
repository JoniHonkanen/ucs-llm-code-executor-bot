from typing import List
import chainlit as cl
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage
import subprocess
import shlex
import os

# own imports
from schemas import Code, Codes, GraphState, Documentation, DockerFile
from prompts.prompts import (
    CODE_GENERATOR_AGENT_PROMPT,
    CODE_FIXER_AGENT_PROMPT,
    README_DEVELOPER_WRITER_AGENT_PROMPT,
    DOCKERFILE_GENERATOR_AGENT_PROMPT,
)


# Generate code from user input
async def code_generator_agent(state: GraphState, llm) -> GraphState:
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
    state["messages"] += [AIMessage(content=f"{generated_code.description}")]

    # loop through the codes
    for code in state["codes"].codes:
        state["messages"] += [
            AIMessage(
                content=f"Description of code: {code.description} \n Programming language used: {code.programming_language} \n {code.code}"
            )  # TODO: pitääkö generated_code2.codes for loopata codes läpi? varmaan pitää
        ]
        await cl.Message(content=code.code, language=code.programming_language).send()

    return state


# Save generated code to file
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


# Execute code from folder (will be replaced with dockerizer agent?)
async def execute_code_agent(state: GraphState, code_file):
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
            print(result)
            error = f"Execution failed with error: {result.stderr}"
        print(result.stdout)

    except Exception as e:
        print("Found Error While Running")
        error = f"Execution Error : {e}"

    if error:
        await cl.Message(content=error).send()

    return {"error": error}


# Debug codes if error occurs
async def debug_code_agent(state: GraphState, llm):
    print("\n **DEBUG CODE**")
    print(state)
    error = state["error"]
    code = state["codes"].codes
    structured_llm = llm.with_structured_output(Codes)
    prompt = CODE_FIXER_AGENT_PROMPT.format(original_code=code, error_message=error)
    fixed_code = structured_llm.invoke(prompt)
    print("\nNEW FIXED CODE:", fixed_code)

    # Update the state with the fixed code
    state["codes"] = fixed_code

    # loop through the codes
    for code in state["codes"].codes:
        state["messages"] += [
            AIMessage(
                content=f"Description of code: {code.description} \n Programming language used: {code.programming_language} \n {code.code}"
            )
        ]
        await cl.Message(content=code.code, language=code.programming_language).send()

    # update iterations to state
    state["iterations"] += 1

    return state


# TODO: move this to utils?
# Generate code descriptions for prompt
def generate_code_descriptions(codes: List[Code]) -> str:
    """
    Generate formatted descriptions of the code files for the README and DEVELOPER files.

    Example output:
    **main.py** (Executable)
    Language: python
    Description: This file contains the main execution logic of the program. It imports the greeting and formatting functions and calls them to display the message
    """
    descriptions = []
    for code in codes:
        executable_note = "(Executable)" if code.executable_code else ""
        descriptions.append(
            f"**{code.filename}** {executable_note}\n"
            f"Language: {code.programming_language}\n"
            f"Description: {code.description}"
        )
    return "\n\n".join(descriptions)


# Create readme and developer files
async def read_me_agent(state: GraphState, llm, code_file):
    print("\n **GENERATING README & DEVELOPER FILES **")
    print(state)

    structured_llm = llm.with_structured_output(Documentation)
    code_descriptions = generate_code_descriptions(state["codes"].codes)
    prompt = README_DEVELOPER_WRITER_AGENT_PROMPT.format(
        messages=state["messages"], code_descriptions=code_descriptions
    )

    docs = structured_llm.invoke(prompt)
    readme = docs.readme
    developer = docs.developer
    # save files for root
    with open(code_file + "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    with open(code_file + "DEVELOPER.md", "w", encoding="utf-8") as f:
        f.write(developer)
    return state


# Dockerizer the project
async def dockerizer_agent(state: GraphState, llm, file_path):
    print("\n **DOCKERIZER AGENT **")
    print(state)
    structured_llm = llm.with_structured_output(DockerFile)
    code_descriptions = generate_code_descriptions(state["codes"].codes)
    prompt = DOCKERFILE_GENERATOR_AGENT_PROMPT.format(
        messages=state["messages"], code_descriptions=code_descriptions
    )
    docker_things = structured_llm.invoke(prompt)
    print("\n description: " + docker_things.description)
    print("\n dockerfile: " + docker_things.dockerfile)
    print("\n docker_compose: " + docker_things.docker_compose)
    print("\nfolder_watching: " + docker_things.folder_watching)
    # save files using file_path
    with open(file_path + "Dockerfile", "w", encoding="utf-8") as f:
        f.write(docker_things.dockerfile)
    with open(file_path + "docker-compose.yml", "w", encoding="utf-8") as f:
        f.write(docker_things.docker_compose)
    return state
