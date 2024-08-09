from langchain_core.prompts import ChatPromptTemplate

#Agent for creating code from user input
CODE_GENERATOR_AGENT = ChatPromptTemplate.from_template(
"""**Role**: You are a expert software python programmer. You need to develop python code
**Task**: As a programmer, you are required to complete the function. Use a Chain-of-Thought approach to break
down the problem, create pseudocode, and then write the code in Python language. Ensure that your code is
efficient, readable, and well-commented.
**Instructions**:
1. **Understand and Clarify**: Make sure you understand the task.
2. **Algorithm/Method Selection**: Decide on the most efficient way.
3. **Pseudocode Creation**: Write down the steps you will follow in pseudocode.
4. **Code Generation**: Translate your pseudocode into executable Python code
*REQURIEMENT*
{requirement}"""
)

def discover_function(state):
    print("*************************Executing discover_function with state:", state)
    # State
    messages = state["messages"]
    iterations = state["iterations"]
    error = state["error"]
    # Using the with_structured_output method
    # structured_llm  = llm.with_structured_output(Code, method="json_mode")
    structured_llm = llm.with_structured_output(Code)

    # Format the prompt with the requirement
    # requirement = "Generate Fibonacci series as JSON with `description` and `code` keys"
    requirement = "Hello world program in python"
    prompt = CODE_GENERATOR_AGENT.format(requirement=requirement)

    # Invoke the coder with the formatted prompt
    generated_code = structured_llm.invoke(prompt)
    print("Generated code:", generated_code)

    # Update the state with the generated code
    state["class_source"] = "asd"

    return {"generation": "asd", "messages": ["asd", "asd"], "iterations": 1}