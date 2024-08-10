from langchain_openai import ChatOpenAI
import configparser

config = configparser.ConfigParser()
config.read("config.ini")
llm_config = config["LLM"]

#model name from config.ini
def get_openai_llm():
    return ChatOpenAI(model=llm_config["model"])