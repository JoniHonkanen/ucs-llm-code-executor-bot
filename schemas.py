from typing import List, TypedDict, Optional
from langchain_core.pydantic_v1 import BaseModel, Field, Extra, validator


# Schema for single code file
class Code(BaseModel):
    """
    Represents an individual piece of code generated as part of a programming project.
    """

    description: str = Field(
        description="A detailed description of what this specific code does and its purpose."
    )
    filename: str = Field(
        description="The name of the file in which this code is saved."
    )
    executable_code: bool = Field(
        description=(
            "Indicates whether this code is the main executable file required for the "
            "program to run. There should only be one executable file in the project structure."
        )
    )
    # relationship: str = Field(description="Relationship between this code and other files/folders in the project")
    code: str = Field(
        description="The actual code written in the specified programming language. Do not add any newlines using'\n'"
    )
    programming_language: str = Field(
        description="The programming language used to write this code."
    )


# Schema for whole code project
class Codes(BaseModel):
    """
    Represents a collection of multiple code files generated as part of a programming project.
    """

    description: str = Field(
        description=(
            "A detailed description of the entire set of codes generated. "
            "This includes how the different pieces of code work together, their individual purposes, "
            "and any relationships or dependencies between them."
        )
    )
    codes: List[Code] = Field(
        description="A list containing all the code files generated as part of the project."
    )
    execution_command: str = Field(
        description="The command used to execute the main executable file in the project."
    )


class FixedCode(BaseModel):
    """
    Represents an individual piece of code generated as part of a programming project.
    """

    description: str = Field(
        description="A detailed description of what was fixed in this specific code and its purpose."
    )
    filename: str = Field(description="The orginal filename")
    executable_code: bool = Field(
        description=(
            "Indicates whether this code is the main executable file required for the "
            "program to run. There should only be one executable file in the project structure."
        )
    )
    # relationship: str = Field(description="Relationship between this code and other files/folders in the project")
    code: str = Field(
        description="The actual code that have been fully fixed. Do not add any newlines using'\n'"
    )
    programming_language: str = Field(
        description="The programming language used to write this code."
    )


# Schema for generated project Readme.md and Developer.md files
class Documentation(BaseModel):
    """
    readme.md & developer.md
    """

    readme: str = Field(description="The readme file")
    developer: str = Field(description="The developer file")


# Schema for Dockerfile and Docker Compose configuration
class DockerFile(BaseModel):
    """
    Represents the Dockerfile and Docker Compose configuration for a software project.
    Attributes:
        description : A detailed description of the Docker setup for the software project.
        dockerfile : The content of the Dockerfile used to build the Docker image for the project.
        docker_compose : The content of the Docker Compose configuration file used to manage and orchestrate the Docker services.
    """

    description: str = Field(
        description=(
            "A detailed explanation of the Docker setup for the software project. "
            "This includes the purpose of using Docker, the rationale behind the choices made in the Dockerfile "
            "and Docker Compose file, and any specific configurations or optimizations for development and deployment. "
            "It should also touch on how folder watching is implemented and the expected behavior when code changes."
        )
    )
    dockerfile: str = Field(
        description="The complete content of the Dockerfile, detailing all the instructions needed to build the Docker image, including base image selection, dependency installation, file copying, and the final command to run the application."
    )
    docker_compose: str = Field(
        description="The full content of the Docker Compose configuration file, which defines how the Docker services are managed and orchestrated, including service definitions, volume mounting, environment variables, and any network configurations."
    )
    docker_image_name: str = Field(
        description="The name of the Docker image built for the project, which is used to identify the image in the local Docker registry."
    )
    docker_container_name: str = Field(
        description="The name of the Docker container created from the Docker image, which is used to identify the running container instance."
    )

class ErrorMessage(BaseModel):
    """
    Represents a structured error message.

    Attributes:
        type: The type of error (e.g., 'Internal Code Error', 'Dependency Error', 'Execution Error').
        details:  detailed information or stack trace related to the error.
        code_reference:  reference to the part of the code where the error occurred (e.g., filename, function name, line number).
    """

    type: str
    details: str
    file: Optional[str] = None
    line: Optional[int] = None
    code_reference: Optional[str] = None


# include texts from Dockerfile and compose.yaml
class DockerFiles(BaseModel):
    dockerfile: str
    docker_compose: str


# State of the graph (agents)
class GraphState(TypedDict):
    """
    Represents the state of our graph.

    Attributes:
        error : Binary flag for control flow to indicate whether test error was tripped
        messages : With user question, error messages, reasoning
        code : Code solution
        iterations : Number of tries
    """

    error: ErrorMessage  # error messages
    messages: List  # all messages
    codes: Codes  # A collection of code files
    docker_files: DockerFiles  # dockerFile, dockerCompose
    docker_image_name: str  # Name of the Docker image
    docker_container_name: str  # Name of the Docker container
    executable_file_name: str  # What is the name of the executable file
    iterations: int  # Number of tries
