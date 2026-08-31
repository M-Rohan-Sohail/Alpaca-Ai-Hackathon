import os
import json
import logging
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

class AlpacaMCPClient:
    def __init__(self):
        # We explicitly resolve the binary installed in the agentic_env
        self.command = "/home/rohaanloq69/agentic_env/bin/alpaca-mcp-server"
        
        if not os.path.exists(self.command):
            # Fallback to PATH if not found in absolute path
            self.command = "alpaca-mcp-server"
            
        self.session = None
        self._exit_stack = AsyncExitStack()

    async def connect(self):
        """Initializes the MCP Server and keeps it awake for the duration of the context."""
        env = os.environ.copy()
        
        server_params = StdioServerParameters(
            command=self.command,
            args=[],
            env=env
        )
        
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        read, write = stdio_transport
        self.session = await self._exit_stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def disconnect(self):
        """Closes the MCP Server."""
        await self._exit_stack.aclose()
        self.session = None
            
    async def call_tool(self, tool_name: str, args: dict):
        """
        Executes a tool on the persistent MCP server and returns the parsed result.
        """
        if not self.session:
            raise RuntimeError("MCP Client is not connected. Call connect() first.")
            
        try:
            # Discover tools
            available = await self.session.list_tools()
            tool_names = [t.name for t in available.tools]
            if tool_name not in tool_names:
                raise ValueError(f"MCP Tool '{tool_name}' not available. Available: {tool_names}")
                
            # Execute tool
            logger.info(f"Executing MCP Tool: {tool_name}")
            result = await self.session.call_tool(tool_name, args)
            
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
