import requests
from langchain.tools import Tool
from typing import List
import json

class MCPDynamicAdapter:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.tools_cache = None
    
    def get_available_tools(self) -> List[dict]:
        """Obtiene la lista de herramientas del servidor MCP"""
        try:
            response = requests.get(f"{self.base_url}/list_tools")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error obteniendo herramientas: {e}")
            return []

    def load_tools(self) -> List[Tool]:
        """Carga las herramientas como objetos Tool de LangChain"""
        if self.tools_cache:
            return self.tools_cache

        tools_info = self.get_available_tools()
        tools = []
        
        for tool_info in tools_info:
            tool = Tool(
                name=tool_info['name'],
                func=lambda input, tn=tool_info['name']: self.execute_tool(tn, input),
                description=tool_info['description']
            )
            tools.append(tool)
        
        self.tools_cache = tools
        return tools

    def execute_tool(self, tool_name: str, input_data: str):
        """Ejecuta una herramienta específica en el MCP"""
        try:
            response = requests.post(
                f"{self.base_url}/{tool_name}",
                json={"input": input_data},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            return f"Error ejecutando herramienta: {str(e)}"