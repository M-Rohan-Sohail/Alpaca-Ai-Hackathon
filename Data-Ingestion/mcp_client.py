import os
import json
import logging
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

logger = logging.getLogger(__name__)

class AlpacaMCPClient:
    def __init__(self):
        # We explicitly resolve the binary installed in the agentic_env
        self.command = "/home/rohaanloq69/agentic_env/bin/alpaca-mcp-server"
        
        if not os.path.exists(self.command):
            # Fallback to PATH if not found in absolute path
            self.command = "alpaca-mcp-server"
            
    async def call_tool(self, tool_name: str, args: dict):
        """
        Connects to the Alpaca MCP server via stdio, executes a tool, and returns the parsed result.
        Raises an Exception if the MCP server fails, to prevent silent fallback to alpaca-py.
        """
        env = os.environ.copy()
        
        server_params = StdioServerParameters(
            command=self.command,
            args=[],
            env=env
        )
        
        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    
                    # Discover tools
                    available = await session.list_tools()
                    tool_names = [t.name for t in available.tools]
                    if tool_name not in tool_names:
                        raise ValueError(f"MCP Tool '{tool_name}' not available. Available: {tool_names}")
                        
                    # Execute tool
                    logger.info(f"Executing MCP Tool: {tool_name}")
                    result = await session.call_tool(tool_name, args)
                    
                    if result.isError:
                        raise RuntimeError(f"MCP Tool '{tool_name}' returned an error: {result.content}")
                        
                    # Log MCP Evidence
                    import datetime
                    evidence = {
                        "source": "alpaca_mcp",
                        "tool": tool_name,
                        "status": "success",
                        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                    }
                    print(f"\n[MCP EVIDENCE LOG] {json.dumps(evidence)}")
                    
                    if not result.content:
                        return None
                        
                    # Attempt JSON parse if applicable
                    text_content = result.content[0].text
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError:
                        return text_content
                        
        except Exception as e:
            logger.error(f"FATAL: MCP Client failed to call '{tool_name}': {e}")
            raise
