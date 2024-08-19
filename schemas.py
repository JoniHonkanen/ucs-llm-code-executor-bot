from typing import List, TypedDict
from langchain_core.pydantic_v1 import BaseModel, Field, Extra, validator


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


class Documentation(BaseModel):
    """
    readme.md & developer.md
    """

    readme: str = Field(description="The readme file")
    developer: str = Field(description="The developer file")


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
