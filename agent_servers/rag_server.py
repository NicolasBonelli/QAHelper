from fastmcp import FastMCP
from pydantic import BaseModel

mcp = FastMCP(
    name="rag_agent",
    instructions="Agente RAG con dos tools"
)




app = mcp.http_app()  # ✅ para ASGI


@mcp.tool
def tool_a(input_data: str):
    return input_data

@mcp.tool
def tool_b(input_data: str):
    return input_data

if __name__ == "__main__":
    mcp.run()