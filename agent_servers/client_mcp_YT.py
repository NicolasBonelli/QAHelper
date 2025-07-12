import asyncio
import nest_asyncio
from mcp import ClientSession
from mcp.client.sse import sse_client

nest_asyncio.apply()

async def main():
    async with sse_client("http://localhost:8050/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools_result = await session.list_tools("list_tools")
                print("Available tools:")
                for tool in tools_result.tools:
                     print(f" - {tool.name}: {tool.description}")

                result = await session.call_tool("search_documents", arguments={"query": "perro"})
                print (f"Perro search result: {result.content[0].text}")



if __name__ == "__main__":
     asyncio.run(main())