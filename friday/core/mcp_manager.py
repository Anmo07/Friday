import asyncio
import json
import logging
import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: Dict[str, Any]


class MCPManager:
    def __init__(self, config_path: str = "mcp-config.json"):
        self.config_path = config_path
        self.tools: Dict[str, ToolDefinition] = {}
        self._load_config()
        self._register_default_tools()

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.config = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load MCP config: {e}")
                self.config = {"allowed_commands": [], "restricted_paths": []}
        else:
            self.config = {
                "allowed_commands": ["ls", "pwd", "date", "uptime", "python3"],
                "restricted_paths": ["/etc", "/var"],
            }
            self._save_config()

    def _save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f, indent=4)

    def _register_default_tools(self):
        self.register_tool(
            "run_shell_command",
            "Execute a safe local shell command and return the output.",
            {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to run (e.g., 'ls -la')",
                    },
                },
                "required": ["command"],
            },
        )
        self.register_tool(
            "read_local_file",
            "Read the contents of a local file.",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file",
                    },
                },
                "required": ["path"],
            },
        )
        self.register_tool(
            "run_python_script",
            "Execute a Python script and return the output.",
            {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "The Python code to execute",
                    },
                },
                "required": ["code"],
            },
        )
        self.register_tool(
            "get_system_load",
            "Get current CPU and memory usage of the MacBook.",
            {"type": "object", "properties": {}},
        )

    def register_tool(self, name: str, description: str, parameters: Dict[str, Any]):
        self.tools[name] = ToolDefinition(
            name=name, description=description, parameters=parameters
        )

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools.values()
        ]

    async def execute_tool(self, name: str, arguments: Dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Error: Tool '{name}' not found."
        try:
            handler = getattr(self, f"_handle_{name}", None)
            if handler:
                return await handler(**arguments)
            return f"Error: No handler implemented for tool '{name}'."
        except Exception as e:
            logger.error(f"Tool execution failed ({name}): {e}")
            return f"Error: {str(e)}"

    async def _handle_run_shell_command(self, command: str) -> str:
        base_cmd = command.split()[0]
        if base_cmd not in self.config.get("allowed_commands", []):
            return f"Error: Command '{base_cmd}' is not in the allowlist."
        try:
            process = await asyncio.create_subprocess_shell(
                command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if stderr:
                return f"Output: {stdout.decode()}\nError: {stderr.decode()}"
            return stdout.decode() or "Command executed successfully."
        except Exception as e:
            return f"Execution failed: {str(e)}"

    async def _handle_read_local_file(self, path: str) -> str:
        abs_path = os.path.abspath(path)
        for restricted in self.config.get("restricted_paths", []):
            if abs_path.startswith(restricted):
                return f"Error: Access to path '{path}' is restricted."
        if not os.path.exists(abs_path):
            return f"Error: File '{path}' not found."
        try:
            async with asyncio.Lock():
                with open(abs_path, "r") as f:
                    return f.read(5000)
        except Exception as e:
            return f"Read failed: {str(e)}"

    async def _handle_run_python_script(self, code: str) -> str:
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as tmp:
                tmp.write(code.encode())
                tmp_path = tmp.name
            process = await asyncio.create_subprocess_exec(
                "python3",
                tmp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            if stderr:
                return f"Output: {stdout.decode()}\nError: {stderr.decode()}"
            return stdout.decode() or "Python script executed successfully."
        except Exception as e:
            return f"Python execution failed: {str(e)}"

    async def _handle_get_system_load(self) -> str:
        try:
            cpu = (
                subprocess.check_output(["sysctl", "-n", "vm.loadavg"]).decode().strip()
            )
            mem = (
                subprocess.check_output(["top", "-l", "1", "-s", "0", "-n", "0"])
                .decode()
                .split("\n")[3]
            )
            return f"System Load (1/5/15 min): {cpu}\nMemory: {mem}"
        except Exception as e:
            return f"Failed to get stats: {str(e)}"


mcp_manager = MCPManager()
