import asyncio
import json
from datetime import date

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client


async def main():
    server_params = StdioServerParameters(
        command="/Users/sanya/Downloads/llm_feature_analytics/venv/bin/python",
        args=["-m", "app.mcp_server"],
        cwd="/Users/sanya/Downloads/llm_feature_analytics",
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            print("TOOLS:")
            print(json.dumps([t.name for t in tools.tools], indent=2))

            result = await session.call_tool(
                "activation_rate",
                {
                    "cohort_start": str(date.today().replace(day=1)),
                    "cohort_end": str(date.today()),
                },
            )

            print("\nRAW RESULT:")
            print(result)

            block = result.content[0]
            if isinstance(block, types.TextContent):
                print("\nTEXT CONTENT:")
                print(block.text)


if __name__ == "__main__":
    asyncio.run(main())