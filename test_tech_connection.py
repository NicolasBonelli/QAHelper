#!/usr/bin/env python3
"""
Test script to verify MCP connection between tech_agent and tech_server
"""

import asyncio
import os
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client

load_dotenv()

async def test_mcp_connection():
    """Test connection to MCP server"""
    server_url = os.getenv("MCP_TECH_SERVER_URL", "http://localhost:8060")
    
    print(f"Testing connection to: {server_url}")
    
    try:
        async with sse_client(f"{server_url}/sse") as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                print("✓ Connected to MCP server")
                
                # Initialize session
                await session.initialize()
                print("✓ Session initialized")
                
                # List tools
                tools_result = await session.list_tools("list_tools")
                print(f"✓ Available tools: {[tool.name for tool in tools_result.tools]}")
                
                # Test generate_excel_from_data
                test_data = "nombre,edad\nJuan,25\nAna,30"
                print(f"Testing generate_excel_from_data with: {test_data}")
                result = await session.call_tool("generate_excel_from_data", arguments={"tabla": test_data})
                print(f"✓ Excel generation result: {result.content[0].text if result.content else 'No content'}")
                
                # Test summarize_text
                test_text = "La inteligencia artificial está transformando la educación moderna."
                print(f"Testing summarize_text with: {test_text}")
                result = await session.call_tool("summarize_text", arguments={"text": test_text})
                print(f"✓ Text summarization result: {result.content[0].text if result.content else 'No content'}")
                
                print("\n🎉 All tests passed!")
                
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Make sure the tech server is running: python agent_servers/tech_server.py")
        print("2. Check if port 8060 is available")
        print("3. Verify MCP_TECH_SERVER_URL environment variable")

if __name__ == "__main__":
    asyncio.run(test_mcp_connection())
