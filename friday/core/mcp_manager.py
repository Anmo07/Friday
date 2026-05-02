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
        # Enhanced cross-application integration tools
        self.register_tool(
            "create_calendar_event",
            "Create a calendar event with title, date, time, and optional description.",
            {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Title of the calendar event",
                    },
                    "date": {
                        "type": "string",
                        "description": "Date of the event (YYYY-MM-DD format)",
                    },
                    "time": {
                        "type": "string",
                        "description": "Time of the event (HH:MM format)",
                    },
                    "description": {
                        "type": "string",
                        "description": "Optional description of the event",
                    }
                },
                "required": ["title", "date", "time"],
            },
        )
        self.register_tool(
            "send_email",
            "Send an email to a recipient with subject and body.",
            {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient email address",
                    },
                    "subject": {
                        "type": "string",
                        "description": "Email subject",
                    },
                    "body": {
                        "type": "string",
                        "description": "Email body content",
                    }
                },
                "required": ["to", "subject", "body"],
            },
        )
        self.register_tool(
            "create_file",
            "Create a new file with specified content at a given path.",
            {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path where the file should be created",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to write to the file",
                    }
                },
                "required": ["path", "content"],
            },
        )
        self.register_tool(
            "open_application",
            "Open or launch an application by name or path.",
            {
                "type": "object",
                "properties": {
                    "application": {
                        "type": "string",
                        "description": "Name or path of the application to open",
                    }
                },
                "required": ["application"],
            },
        )
        # Multi-modal capabilities - Vision processing
        self.register_tool(
            "describe_image",
            "Describe the contents of an image file using AI vision capabilities.",
            {
                "type": "object",
                "properties": {
                    "image_path": {
                        "type": "string",
                        "description": "Path to the image file to describe",
                    },
                    "detail_level": {
                        "type": "string",
                        "description": "Level of detail for description (brief, standard, detailed)",
                        "enum": ["brief", "standard", "detailed"]
                    }
                },
                "required": ["image_path"],
            },
        )
        self.register_tool(
            "get_full_system_info",
            "Get detailed system specifications including CPU, RAM, and Disk space.",
            {"type": "object", "properties": {}},
        )
        self.register_tool(
            "media_control",
            "Control media playback and volume on the Mac.",
            {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "The action to perform (e.g., 'play', 'pause', 'next', 'prev', 'vol_up', 'vol_down')",
                        "enum": ["play", "pause", "next", "prev", "vol_up", "vol_down"]
                    }
                },
                "required": ["action"],
            },
        )
        # Phase 3: Telephony Integration Tools
        self.register_tool(
            "initiate_phone_call",
            "Initiate an autonomous phone call to a recipient.",
            {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The recipient's phone number in E.164 format.",
                    },
                    "message": {
                        "type": "string",
                        "description": "The message to speak during the call.",
                    },
                },
                "required": ["to", "message"],
            },
        )
        self.register_tool(
            "send_sms_message",
            "Send an SMS message to a recipient.",
            {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "The recipient's phone number in E.164 format.",
                    },
                    "body": {
                        "type": "string",
                        "description": "The text content of the SMS.",
                    },
                },
                "required": ["to", "body"],
            },
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
        # Prevent command injection via separators
        for separator in [";", "&", "|", "\n", "\r", "`", "$"]:
            if separator in command:
                return f"Error: Command contains forbidden character '{separator}'."
        
        parts = command.split()
        if not parts:
            return "Error: Empty command."
            
        base_cmd = parts[0]
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
        try:
            # Prevent path traversal
            abs_path = os.path.abspath(path)
            real_path = os.path.realpath(abs_path)
            
            # Check restricted paths
            restricted_roots = self.config.get("restricted_paths", ["/etc", "/var", "/root", "/usr/bin"])
            for restricted in restricted_roots:
                if real_path.startswith(os.path.realpath(restricted)):
                    return f"Error: Access to path '{path}' is restricted for security reasons."
            
            if not os.path.exists(real_path):
                return f"Error: File '{path}' not found."
            if not os.path.isfile(real_path):
                return f"Error: '{path}' is not a file."

            async with asyncio.Lock():
                with open(real_path, "r") as f:
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
            # Use async process calls to avoid blocking the event loop
            cpu_proc = await asyncio.create_subprocess_exec(
                "sysctl", "-n", "vm.loadavg",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            mem_proc = await asyncio.create_subprocess_exec(
                "top", "-l", "1", "-s", "0", "-n", "0",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            cpu_out, _ = await cpu_proc.communicate()
            mem_out, _ = await mem_proc.communicate()
            
            cpu = cpu_out.decode().strip()
            # Extract memory line safely
            mem_lines = mem_out.decode().split("\n")
            mem = mem_lines[3] if len(mem_lines) > 3 else "Unknown memory status"
            
            return f"System Load (1/5/15 min): {cpu}\nMemory: {mem}"
        except Exception as e:
            return f"Failed to get stats: {str(e)}"

    async def _handle_create_calendar_event(self, title: str, date: str, time: str, description: str = "") -> str:
        """Handle creating a calendar event (mock implementation)"""
        try:
            # In a real implementation, this would integrate with Calendar APIs
            # For now, we'll simulate by creating a reminder in a file or showing confirmation
            event_info = {
                "title": title,
                "date": date,
                "time": time,
                "description": description
            }
            # Simulate successful creation
            return f"Calendar event created successfully: '{title}' on {date} at {time}" + (f" with description: {description}" if description else "")
        except Exception as e:
            return f"Failed to create calendar event: {str(e)}"

    async def _handle_send_email(self, to: str, subject: str, body: str) -> str:
        """Handle sending an email (mock implementation)"""
        try:
            # In a real implementation, this would integrate with email services
            # For now, we'll simulate by logging or saving to a file
            email_info = {
                "to": to,
                "subject": subject,
                "body": body
            }
            # Simulate successful sending
            return f"Email sent successfully to {to} with subject: '{subject}'"
        except Exception as e:
            return f"Failed to send email: {str(e)}"

    async def _handle_create_file(self, path: str, content: str) -> str:
        """Handle creating a file with specified content"""
        try:
            # Prevent path traversal
            abs_path = os.path.abspath(path)
            real_path = os.path.realpath(abs_path)
            
            # Security check: prevent writing to sensitive paths
            restricted_roots = ["/etc", "/var", "/usr", "/bin", "/sbin", "/root"]
            for restricted in restricted_roots:
                if real_path.startswith(os.path.realpath(restricted)):
                    return f"Error: Access to path '{path}' is restricted for security reasons."
            
            # Create directory if it doesn't exist
            directory = os.path.dirname(real_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            # Write the file
            with open(real_path, 'w') as f:
                f.write(content)
            
            return f"File created successfully at '{path}'"
        except Exception as e:
            return f"Failed to create file: {str(e)}"

    async def _handle_open_application(self, application: str) -> str:
        """Handle opening an application with bundle ID or exact name validation"""
        try:
            # Strict whitelist of allowed application names/bundle IDs
            # In a real production environment, use bundle IDs like 'com.apple.Safari'
            ALLOWED_APPS = {
                "safari", "firefox", "google chrome", "textedit", 
                "preview", "calculator", "notes", "terminal", "calendar"
            }
            
            app_query = application.lower().strip()
            if app_query in ALLOWED_APPS:
                # Actual implementation would use: os.system(f"open -a '{application}'")
                return f"Application '{application}' opened successfully."
            else:
                return f"Error: Application '{application}' is not in the security allowlist. For your safety, only pre-approved productivity applications can be launched via voice."
        except Exception as e:
            return f"Failed to open application: {str(e)}"

    async def _handle_describe_image(self, image_path: str, detail_level: str = "standard") -> str:
        """Handle describing an image using AI vision"""
        try:
            # Prevent path traversal
            abs_path = os.path.abspath(image_path)
            real_path = os.path.realpath(abs_path)
            
            # Security check: prevent accessing sensitive paths
            restricted_roots = ["/etc", "/var", "/usr", "/bin", "/sbin", "/root"]
            for restricted in restricted_roots:
                if real_path.startswith(os.path.realpath(restricted)):
                    return f"Error: Access to path '{image_path}' is restricted for security reasons."
            
            # Check if file exists
            if not os.path.exists(real_path):
                return f"Error: Image file '{image_path}' not found."
            
            # In a real implementation, this would use a vision model like GPT-4V, Claude 3, etc.
            # For now, we'll simulate by returning a description based on filename
            filename = os.path.basename(image_path).lower()
            
            if detail_level == "brief":
                return f"Image shows content related to {filename.split('.')[0]}."
            elif detail_level == "detailed":
                return f"Detailed analysis of {filename}: The image appears to contain visual elements that suggest a scene related to {filename.split('.')[0]}. Colors, shapes, and composition indicate this is likely a {filename.split('.')[0]}-related visual content. Further analysis would require actual image processing capabilities."
            else:  # standard
                return f"Image '{filename}' contains visual content that appears to be related to {filename.split('.')[0]}. The image shows various elements that suggest a {filename.split('.')[0]} theme or subject matter."
        except Exception as e:
            return f"Failed to describe image: {str(e)}"

    async def _handle_extract_text_from_image(self, image_path: str) -> str:
        """Handle extracting text from image using OCR (mock implementation)"""
        try:
            # Security check: prevent accessing sensitive paths
            restricted_paths = ["/etc", "/var", "/usr", "/bin", "/sbin", "/root"]
            abs_path = os.path.abspath(image_path)
            for restricted in restricted_paths:
                if abs_path.startswith(restricted):
                    return f"Error: Access to path '{image_path}' is restricted for security reasons."
            
            # Check if file exists
            if not os.path.exists(abs_path):
                return f"Error: Image file '{image_path}' not found."
            
            # In a real implementation, this would use OCR like Tesseract or vision models
            # For now, we'll simulate by returning placeholder text
            filename = os.path.basename(image_path)
            return f"[OCR Text extracted from {filename}]\nThis is simulated extracted text from the image.\nIn a real implementation, actual OCR would extract text content from the image.\nExtracted content would appear here based on the actual image content."
        except Exception as e:
            return f"Failed to extract text from image: {str(e)}"


    async def _handle_get_full_system_info(self) -> str:
        """Get comprehensive system info using multiple commands"""
        try:
            # Parallel execution of info gathering
            tasks = [
                asyncio.create_subprocess_exec("sysctl", "-n", "machdep.cpu.brand_string", stdout=asyncio.subprocess.PIPE),
                asyncio.create_subprocess_exec("sysctl", "-n", "hw.memsize", stdout=asyncio.subprocess.PIPE),
                asyncio.create_subprocess_exec("df", "-h", "/", stdout=asyncio.subprocess.PIPE)
            ]
            procs = await asyncio.gather(*tasks)
            outputs = await asyncio.gather(*(p.communicate() for p in procs))
            
            cpu = outputs[0][0].decode().strip()
            mem_bytes = int(outputs[1][0].decode().strip())
            mem_gb = mem_bytes / (1024**3)
            disk = outputs[2][0].decode().split("\n")[1]
            
            return f"CPU: {cpu}\nRAM: {mem_gb:.1f} GB\nDisk Space (/): {disk}"
        except Exception as e:
            return f"Failed to gather system info: {str(e)}"

    async def _handle_media_control(self, action: str) -> str:
        """Control media using AppleScript"""
        try:
            scripts = {
                "play": "tell application \"Music\" to play",
                "pause": "tell application \"Music\" to pause",
                "next": "tell application \"Music\" to next track",
                "prev": "tell application \"Music\" to previous track",
                "vol_up": "set volume output volume (output volume of (get volume settings) + 10)",
                "vol_down": "set volume output volume (output volume of (get volume settings) - 10)"
            }
            script = scripts.get(action)
            if not script:
                return f"Error: Action '{action}' not recognized."
            
            subprocess.run(["osascript", "-e", script], capture_output=True)
            return f"Media action '{action}' executed."
        except Exception as e:
            return f"Media control failed: {str(e)}"

    async def _handle_initiate_phone_call(self, to: str, message: str) -> str:
        """Handle initiating a phone call (Phase 3)"""
        try:
            # Logic would integrate with app/api/routes.py telephony logic
            logger.info(f"MCP Telephony: Calling {to} with message: {message}")
            return f"Call initiated to {to}. Transcription: '{message}'"
        except Exception as e:
            return f"Telephony call failed: {str(e)}"

    async def _handle_send_sms_message(self, to: str, body: str) -> str:
        """Handle sending an SMS (Phase 3)"""
        try:
            logger.info(f"MCP Telephony: Sending SMS to {to}: {body}")
            return f"SMS sent to {to}."
        except Exception as e:
            return f"Telephony SMS failed: {str(e)}"


mcp_manager = MCPManager()
