from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv
print()
load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    temperature=0,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

response = llm.invoke("¿Qué es FastAPI?")
print(response)