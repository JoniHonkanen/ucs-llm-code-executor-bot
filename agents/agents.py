import inspect
import asyncio
import subprocess
import shlex
import os
import docker
import chainlit as cl
import time
from docker.errors import APIError, ContainerError
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage

# own imports
from schemas import (
    Code,
    Codes,
    FixedCode,
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

    # Store the Dockerfile and Docker Compose configuration in the state
    # Create an instance of DockerFiles
    docker_files_instance = DockerFiles(
        dockerfile=docker_things.dockerfile, docker_compose=docker_things.docker_compose
    )

    # Store the instance in the state dictionary
    state["docker_files"] = docker_files_instance
    state["docker_image_name"] = docker_things.docker_image_name
    state["docker_container_name"] = docker_things.docker_container_name
    # Use os.path.join to construct full file paths
    dockerfile_path = os.path.join(file_path, "Dockerfile")
    docker_compose_path = os.path.join(file_path, "compose.yaml")

    # Update the message state with the generated Dockerfile and Docker Compose configuration
    state["messages"] += [
        AIMessage(content=f"Description of dockerfile: {docker_things.description}"),
        AIMessage(content=f"Dockerfile: {docker_things.dockerfile}"),
        AIMessage(content=f"Docker.yaml: {docker_things.docker_compose}"),
        AIMessage(content=f"Docker image name: {docker_things.docker_image_name}"),
        AIMessage(
            content=f"Docker container name: {docker_things.docker_container_name}"
        ),
    ]

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

    # Use container name from state
    container_name = state["docker_container_name"]

    try:
        # Phase 1: Docker Setup and Build
        print(f"Building and starting Docker container: {container_name}...")

        # Run docker-compose up --build
        compose_file_path = os.path.join(file_path, "compose.yaml")
        compose_command = ["docker-compose", "-f", compose_file_path, "up", "--build"]

        setup_process = await asyncio.create_subprocess_exec(
            *compose_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        setup_stdout, setup_stderr = await setup_process.communicate()

        if setup_process.returncode != 0:
            error = ErrorMessage(
                type="Docker Configuration Error",
                message="Error during Docker setup or build process.",
                details=setup_stderr.decode().strip(),
                code_reference=f"{current_file} - {current_function}",
            )
            print(f"Error during Docker setup: {setup_stderr.decode()}")
            return {"error": error}

        print("Docker setup and build completed successfully.")
        print("Docker Setup Output:\n", setup_stdout.decode())

        # Phase 2: Fetch logs from the container
        print(f"Fetching logs from the container: {container_name}...")

        log_process = await asyncio.create_subprocess_exec(
            "docker",
            "logs",
            container_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        log_stdout, log_stderr = await log_process.communicate()
        logs = log_stdout.decode()

        if "Traceback" in logs or "Error" in logs or log_stderr.decode().strip():
            error = ErrorMessage(
                type="Docker Execution Error",
                message="The code inside the container encountered an error.",
                details=log_stderr.decode().strip(),
                code_reference=f"{current_file} - {current_function}",
            )
            print(f"Error during container execution: {log_stderr.decode()}")
        else:
            print("Container Logs:\n", logs)

    except Exception as e:
        error = ErrorMessage(
            type="Unexpected Docker Error",
            message="An unexpected error occurred while communicating with Docker.",
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
            f"{file_path}/compose.yaml",
            "down",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except Exception as stop_error:
        print(f"Failed to stop Docker container: {str(stop_error)}")


# DEBUGGING FOR SPECIFIC USE CASES
# Debug codes if error occurs
async def debug_docker_execution_agent(state: GraphState, llm, file_path):
    print("\n **DEBUG DOCKER AGENT**")
    # update docker file so that will run successfully
    # 1. Check the error message and identify the issue in the Docker configuration.
    # 2. Update the Dockerfile and Docker Compose configuration to fix the error.
    # 3. Save the updated Docker files to the project directory.
    # 4. Re-run the Docker setup to verify the fix.

    error = state["error"]
    docker_files = state["docker_files"]
    dockerFile = docker_files.dockerfile
    dockerCompose = docker_files.docker_compose
    structured_llm = llm.with_structured_output(DockerFile)
    prompt = DEBUG_DOCKER_FILES_AGENT_PROMPT.format(
        dockerfile=dockerFile,
        docker_compose=dockerCompose,
        error_messages=error.details,
        messages=state["messages"],
    )
    fixed_docker_files = structured_llm.invoke(prompt)

    # update iterations to state
    state["iterations"] += 1

    dockerfile_path = os.path.join(file_path, "Dockerfile")
    docker_compose_path = os.path.join(file_path, "compose.yaml")
    # Save files using the constructed paths
    with open(dockerfile_path, "w", encoding="utf-8") as f:
        f.write(fixed_docker_files.dockerfile)
    with open(docker_compose_path, "w", encoding="utf-8") as f:
        f.write(fixed_docker_files.docker_compose)
    return state


# Debug code used in docker if error occurs
async def debug_code_execution_agent(state: GraphState, llm, file_path):
    print("\n **DEBUG CODE**")
    error = state["error"]
    code_list = state["codes"].codes
    structured_llm = llm.with_structured_output(Code)

    # Create the prompt for the LLM to suggest a fix
    prompt = CODE_FIXER_AGENT_PROMPT.format(
        original_code=code_list, error_message=error
    )
    fixed_code = structured_llm.invoke(prompt)

    print("\nOriginal Codes, one should be replaced:", code_list)
    print("\nNew Fixed Code:", fixed_code)
    print("\n\nAbove is the code to be updated.")

    # Directly updating the relevant code in the list by matching filenames
    for code in code_list:
        if code.filename == fixed_code.filename:
            code.description = fixed_code.description
            code.code = fixed_code.code
            break  # Exit the loop once the matching code is found and updated

    state["codes"].codes = code_list
    state["iterations"] += 1

    # Save the fixed code to the respective file
    full_file_path = os.path.join(file_path, fixed_code.filename)

    # Write the updated code to the file, replacing '\n' placeholders with actual newlines
    formatted_code = fixed_code.code.replace("\\n", "\n")
    with open(full_file_path, "w") as f:
        f.write(formatted_code)

    return state


# Agent for logging container for errors using docker logs (code related errors!)
async def log_docker_container_errors(state: GraphState):
    print("\n** LOG DOCKER CONTAINER ERRORS AGENT **")

    container_name = state["docker_container_name"]
    client = docker.from_env()
    error = None  # Initialize error as None
    check_interval = 1  # Check every 1 second
    monitor_duration = 3  # Total time to monitor for errors (in seconds)
    start_time = time.time()

    try:
        # Get the Docker container by name
        container = client.containers.get(container_name)
        print(
            f"Monitoring logs for container: {container_name} for {monitor_duration} seconds."
        )

        while True:
            try:
                # Fetch the last 20 lines of logs from the container
                logs = container.logs(tail=20).decode("utf-8")
                print("\nContainer Logs:\n", logs)

                # Check for real errors in the logs (stack traces, exceptions, etc.)
                error_message = parse_error_from_logs(logs)
                if error_message:
                    print(f"Error detected: {error_message.details}")

                    # Set the error variable
                    error = error_message
                    break  # Stop monitoring after detecting the error

                # If no real errors, continue monitoring
                print("No critical errors detected in the logs.")

                # Check if 3 seconds have passed since monitoring started
                elapsed_time = time.time() - start_time
                if elapsed_time >= monitor_duration:
                    print(f"No errors detected after {monitor_duration} seconds.")
                    error = None  # No errors detected
                    break  # Stop monitoring after the timeout

            except Exception as e:
                print(f"Failed to retrieve logs or process container: {e}")
                error = ErrorMessage(type="Internal Code Error", details=str(e))
                break  # Stop monitoring after encountering an internal error

            # Wait for the specified interval before checking logs again
            await asyncio.sleep(check_interval)

    except docker.errors.NotFound:
        print(f"Error: Container '{container_name}' not found.")
        error = ErrorMessage(
            type="Container Not Found",
            details=f"Container '{container_name}' not found.",
        )
    except Exception as e:
        print(f"An error occurred: {e}")
        error = ErrorMessage(type="Internal Code Error", details=str(e))

    # Return the error variable, which may be None if no error was found
    return {"error": error}


def parse_error_from_logs(logs: str) -> ErrorMessage:
    """
    Parse the logs to extract error details and return an ErrorMessage object.
    This function is enhanced to detect actual stack traces, exceptions, or other critical patterns.
    """
    error_type = "Execution Error"

    # critical_error_keywords = [
    # "traceback", "exception", "failed", "critical", "syntaxerror",
    # "indentationerror", "nameerror", "typeerror", "valueerror",
    # "importerror", "modulenotfounderror", "indexerror", "keyerror",
    # "attributeerror", "zerodivisionerror", "oserror", "runtimeerror",
    # "memoryerror", "timeouterror", "recursionerror"
    # ]

    # Example: Look for specific patterns like "Traceback", "Exception", or other critical failure terms
    critical_error_keywords = [
        "traceback",
        "exception",
        "failed",
        "critical",
        "syntaxerror",
    ]

    error_lines = [
        line
        for line in logs.splitlines()
        if any(keyword in line.lower() for keyword in critical_error_keywords)
    ]

    if error_lines:
        error_details = "\n".join(error_lines)
        return ErrorMessage(type=error_type, details=error_details)

    return None  # No real error detected
