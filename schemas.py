from typing import List, TypedDict
from langchain_core.pydantic_v1 import BaseModel, Field, Extra, validator

class Code(BaseModel):
    """Plan to follow in future"""

    description: str = Field(description="Detailed description of the code generated")
    code: str = Field(description="Python code generated based on the requirements")

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
    code: Code
    iterations: int
