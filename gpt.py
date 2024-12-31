import os
from os import getenv
import openai
from dotenv import load_dotenv; load_dotenv()
from openai.error import APIConnectionError

openai.api_key = getenv("OPENAI_KEY")

class CHATGPT():
    def __init__(self, prompt:dict, model:str="gpt-3.5-turbo") -> None:
        self._prompt =  prompt
        self._model = model
    def request(self,content:str, retry:int=0) -> str:
        try:

            _response =  openai.ChatCompletion.create(
                model = self._model,
                messages = [
                    {
                        "role":"user",
                        "content":content
                    }
                ]
            )
            return _response["choices"][0]["message"]["content"]
        except APIConnectionError:
            return None


ChatGPT = CHATGPT(prompt="Tu es un assistant qui permet de gérer une boite mail.")