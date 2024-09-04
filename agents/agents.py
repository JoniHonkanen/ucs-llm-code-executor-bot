import re
import inspect
import asyncio
import subprocess
import shlex
import os
import chainlit as cl
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# own imports
from schemas import (
    Code,
    Codes,
    ErrorMessage,
    GraphState,
    Documentation,
    DockerFile,
    DockerFiles,
)
from prompts.prompts import (
    CODE_GENERATOR_AGENT_PROMPT,
    CODE_FIXER_AGENT_PROMPT,
    README_DEVELOPER_WRITER_AGENT_PROMPT,
    DOCKERFILE_GENERATOR_AGENT_PROMPT,
    DEBUG_DOCKER_FILES_AGENT_PROMPT,
)


# Generate code from user input
async def code_generator_agent(state: GraphState, llm) -> GraphState:
    print("\n**CODE GENERATOR AGENT**")
    # print(state)
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
            )
        ]
        await cl.Message(content=code.code, language=code.programming_language).send()

    return state


# Save generated code to file
def write_code_to_file_agent(state: GraphState, code_file):
    print("\n**WRITE CODE TO FILE**")
    # print(state)

    # Loop through the codes and write them to file
    for code in state["codes"].codes:
        if code.executable_code:
            state["executable_file_name"] = code.filename

        # Construct the full file path
        full_file_path = os.path.join(code_file, code.filename)

        # Ensure the directory exists
        directory = os.path.dirname(full_file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Write the formatted code to the file
        formatted_code = code.code.replace("\\n", "\n")
        with open(full_file_path, "w") as f:
            f.write(formatted_code)

    return state


# Execute code from folder (will be replaced with dockerizer agent?)
async def execute_code_agent(state: GraphState, code_file):
    print("\n**EXECUTE CODE**")
    # print(state)

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
    # print(state)
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
async def read_me_agent(state: GraphState, llm, file_path):
    print("\n **GENERATING README & DEVELOPER FILES **")
    # print(state)

    structured_llm = llm.with_structured_output(Documentation)
    code_descriptions = generate_code_descriptions(state["codes"].codes)
    prompt = README_DEVELOPER_WRITER_AGENT_PROMPT.format(
        messages=state["messages"], code_descriptions=code_descriptions
    )

    docs = structured_llm.invoke(prompt)
    readme = docs.readme
    developer = docs.developer

    # Use os.path.join to construct full file paths
    readme_path = os.path.join(file_path, "README.md")
    developer_path = os.path.join(file_path, "DEVELOPER.md")
    # save files for root
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(readme)
    with open(developer_path, "w", encoding="utf-8") as f:
        f.write(developer)

    return state


# Dockerizer the project
async def dockerizer_agent(state: GraphState, llm, file_path):
    print("\n **DOCKERIZER AGENT **")

    structured_llm = llm.with_structured_output(DockerFile)
    code_descriptions = generate_code_descriptions(state["codes"].codes)

    prompt = DOCKERFILE_GENERATOR_AGENT_PROMPT.format(
        executable_file_name=state["executable_file_name"],
        code_descriptions=code_descriptions,
        messages=state["messages"],
    )

    docker_things = structured_llm.invoke(prompt)

    # Update the message state with the generated Dockerfile and Docker Compose configuration
    state["messages"] += [
        AIMessage(content=f"Description of dockerfile: {docker_things.description}"),
        AIMessage(content=f"Dockerfile: {docker_things.dockerfile}"),
        AIMessage(content=f"Docker.yaml: {docker_things.docker_compose}"),
    ]

    # Store the Dockerfile and Docker Compose configuration in the state
    # Create an instance of DockerFiles
    docker_files_instance = DockerFiles(
        dockerfile=docker_things.dockerfile, docker_compose=docker_things.docker_compose
    )

    # Store the instance in the state dictionary
    state["docker_files"] = docker_files_instance

    # Use os.path.join to construct full file paths
    dockerfile_path = os.path.join(file_path, "Dockerfile")
    docker_compose_path = os.path.join(file_path, "docker-compose.yml")

    # Save files using the constructed paths
    with open(dockerfile_path, "w", encoding="utf-8") as f:
        f.write(docker_things.dockerfile)
    with open(docker_compose_path, "w", encoding="utf-8") as f:
        f.write(docker_things.docker_compose)

    return state


async def execute_docker_agent(state: GraphState, file_path: str):
    print("\n **EXECUTE DOCKER AGENT **")
    error = None
    current_function = inspect.currentframe().f_code.co_name
    current_file = __file__

    try:
        # Phase 1: Docker Setup and Build
        setup_process = await asyncio.create_subprocess_exec(
            "docker-compose",
            "-f",
            f"{file_path}/docker-compose.yml",
            "up",
            "--build",
            "-d",  # Run in detached mode
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        setup_stdout, setup_stderr = await setup_process.communicate()
        setup_stdout_decoded = setup_stdout.decode()
        setup_stderr_decoded = setup_stderr.decode()

        if setup_process.returncode != 0:
            error = ErrorMessage(
                type="Docker Configuration Error",
                message="Error during Docker setup or build process.",
                details=setup_stderr_decoded.strip(),
                code_reference=f"{current_file} - {current_function}",
            )
            # Attempt to stop any containers that might have started
            await stop_docker_containers(file_path)
        else:
            print("Docker Setup Output:\n", setup_stdout_decoded)

        # If no configuration error, proceed to check for execution errors
        if not error:
            # Phase 2: Code Execution
            container_name = "src-hello_world-1"  # Dynamically determine the container name if necessary
            execution_process = await asyncio.create_subprocess_exec(
                "docker",
                "logs",
                container_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            execution_stdout, execution_stderr = await execution_process.communicate()
            execution_stdout_decoded = execution_stdout.decode()

            # Check logs for runtime errors
            if (
                "Traceback" in execution_stdout_decoded
                or "Error" in execution_stdout_decoded
            ):
                error = ErrorMessage(
                    type="Docker Execution Error",
                    message="The code inside the container encountered an error.",
                    details=execution_stdout_decoded.strip(),
                    code_reference=f"{current_file} - {current_function}",
                )

            print("Container Logs:\n", execution_stdout_decoded)

        # Clean up: Stop the Docker container after execution
        await stop_docker_containers(file_path)

    except Exception as e:
        error = ErrorMessage(
            type="Unexpected Error",
            message="An unexpected error occurred.",
            details=str(e),
            code_reference=f"{current_file} - {current_function}",
        )
        print(error.json())

    if error:
        await cl.Message(content=error.json()).send()

    return {"error": error}


async def stop_docker_containers(file_path: str):
    try:
        await asyncio.create_subprocess_exec(
            "docker-compose",
            "-f",
            f"{file_path}/docker-compose.yml",
            "down",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as stop_error:
        print(f"Failed to stop Docker container: {str(stop_error)}")


# DEBUGGING FOR SPECIFIC USE CASES
# Debug codes if error occurs
async def debug_docker_execution_agent(state: GraphState, llm):
    # update docker file so that will run successfully
    # 1. Check the Dockerfile and Docker Compose configuration for any errors or missing dependencies.
    print("\n **DEBUG DOCKER AGENT**")
    error = state["error"]
    docker_files = state["docker_files"]
    dockerFile = docker_files.dockerfile
    dockerCompose = docker_files.docker_compose
    structured_llm = llm.with_structured_output(DockerFile)
    prompt = DEBUG_DOCKER_FILES_AGENT_PROMPT.format(
        dockerfile=dockerFile, docker_compose=dockerCompose, error_message=error.details
    )
    fixed_docker_files = structured_llm.invoke(prompt)
    print("\nNEW FIXED DOCKER FILES:", fixed_docker_files)

    return state


async def debug_code_execution_agent(state: GraphState, llm):
    print("\n **DEBUG CODE**")
    # update code so that will run successfully
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
