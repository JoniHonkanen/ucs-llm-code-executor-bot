from typing import List, TypedDict
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
        folder_watching : The configuration or setup for enabling automatic detection of code changes using folder watching.
    """

    description: str = Field(
        description=(
            "A detailed description of the Docker setup for the software project. "
            "This includes the purpose of using Docker, the configuration options chosen, "
            "and any additional features or functionalities enabled by Docker."
        )
    )
    dockerfile: str = Field(
        description="The content of the Dockerfile used to build the Docker image for the project."
    )
    docker_compose: str = Field(
        description="The content of the Docker Compose configuration file used to manage and orchestrate the Docker services."
    )
    folder_watching: str = Field(
        description=(
            "The configuration or setup for enabling automatic detection of code changes using folder watching. "
            "This should include any tools or scripts used, as well as the specific folders being monitored."
        )
    )


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

    error: str
    messages: List
    codes: Codes
    executable_file_name: str
    iterations: int
