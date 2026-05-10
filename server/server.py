import os
import sys
import logging
from contextvars import ContextVar
from flask import Flask, request, jsonify
from typing import Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from util.config import load_config, copy_files_to_appdata
from util.commands import command_registry
from util.module_registry import module_registry
from util.database import initialize_pool, close_pool
from util.localization import initialize_localization, get_localization_manager


def resource_path(relative_path):
    """Get the absolute path to a resource, works for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), relative_path)


class BotServer:
    """Server that handles bot command and module processing."""
    
    def __init__(self):
        """Initialize the bot server."""
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # File handler for logging to a file
        file_handler = logging.FileHandler("bot_server.log")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        
        # Stream handler for logging to the console
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        
        # Add both handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Load configuration
        self.config = load_config()
        self.prefixes = self._parse_prefixes(self.config.get("command_prefix", "@"))
        
        # Initialize localization with default English
        self._localization = initialize_localization(strings_dir=resource_path("strings"), default_language="en_US")
        self.language = "en_US"  # Default language, will be overridden per-request
        self._request_language = ContextVar("request_language", default="en_US")
        
        # Initialize database connection pool
        self.logger.info("Initializing database connection pool...")
        try:
            initialize_pool()
            self.logger.info("Database connection pool initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize database pool: {e}")
            raise
        
        # Initialize command and module registries
        self.commands = command_registry
        self.commands.set_logger(self.logger)
        self.modules = module_registry
        self.modules.set_logger(self.logger)
        
        # Response queue for collecting responses during command execution
        self._response_queue = []
        
        # Load commands and modules
        if hasattr(sys, '_MEIPASS'):
            copy_files_to_appdata()
            
        self.load_commands()
        self.load_modules()

    def _parse_prefixes(self, raw_prefixes):
        """Normalize command prefixes from config into a list."""
        if isinstance(raw_prefixes, list):
            prefixes = [str(p).strip() for p in raw_prefixes if str(p).strip()]
            return prefixes or ["@"]

        if isinstance(raw_prefixes, str):
            prefixes = [p.strip() for p in raw_prefixes.split(",") if p.strip()]
            return prefixes or ["@"]

        return ["@"]

    def _extract_command(self, chattext: str):
        """Extract command name and args for any configured prefix."""
        for prefix in self.prefixes:
            if chattext.startswith(prefix):
                remainder = chattext[len(prefix):].strip()
                if not remainder:
                    return None
                command_name = remainder.split(" ")[0]
                command_args = remainder[len(command_name):].strip()
                return command_name, command_args
        return None
        
    def load_commands(self):
        """Load commands from the 'cmds' directory."""
        commands_dir = resource_path("cmds")
        self.commands.load_commands(commands_dir)
        self.logger.info(f"Loaded {len(self.commands)} commands from {commands_dir}")
        
    def load_modules(self):
        """Load modules from the 'modules' directory."""
        modules_dir = resource_path("modules")
        if not os.path.exists(modules_dir):
            return
        self.modules.load_modules(modules_dir)
        self.logger.info(f"Loaded {len(self.modules)} modules from {modules_dir}")
        
    def process_message(self, is_team: bool, playername: str, chattext: str, language: str = "en_US") -> List[Dict]:
        """Process a message and return list of responses.
        
        Args:
            is_team: Whether the message is for team chat
            playername: Name of the player
            chattext: The message text
            language: Language code for responses (defaults to en_US)
        """
        # Set language for this request (request-scoped to avoid cross-request bleed).
        self.language = language
        language_token = self._request_language.set(language)
        import time
        start_time = time.time()
        
        try:
            # Clear response queue for this message
            self._response_queue = []

            # Pass to modules that are reading input
            module_start = time.time()
            for module_name, module_instance in self.modules.modules.items():
                if hasattr(module_instance, "process") and getattr(module_instance, "reading_input", True):
                    try:
                        try:
                            response = module_instance.process(playername, is_team, chattext, t=self.t)
                        except TypeError:
                            response = module_instance.process(playername, is_team, chattext)
                        if response:
                            self._response_queue.append({
                                "is_team": is_team,
                                "text": f"{playername}: {response}"
                            })
                    except Exception as e:
                        self.logger.error(f"Error in module '{module_name}' while processing: {e}")
            module_time = time.time() - module_start

            # Process commands if the line starts with any configured prefix
            command_parts = self._extract_command(chattext)
            if command_parts:
                try:
                    command_start = time.time()
                    command_name, command_args = command_parts

                    self.logger.info(f"Executing command: {command_name} with args: {command_args}")
                    res = self.commands.execute(command_name, self, is_team, playername, command_args)

                    if isinstance(res, str):
                        self._response_queue.append({
                            "is_team": is_team,
                            "text": res
                        })
                    command_time = time.time() - command_start
                    self.logger.info(f"Command execution took {command_time:.4f}s")
                except Exception as e:
                    import traceback
                    self.logger.error(f"Error executing command: {e}")
                    self.logger.error(f"Traceback: {traceback.format_exc()}")

            # Return collected responses
            responses = self._response_queue
            self._response_queue = []

            total_time = time.time() - start_time
            self.logger.info(f"Total processing time: {total_time:.4f}s (modules: {module_time:.4f}s)")

            return responses
        finally:
            self._request_language.reset(language_token)

    def get_request_language(self) -> str:
        """Get language for the current request context."""
        return self._request_language.get()
        
    def add_to_chat_queue(self, is_team: bool, chattext: str) -> None:
        """Compatibility method for commands that expect this method."""
        # Commands call this to queue responses - we collect them in _response_queue
        self._response_queue.append({
            "is_team": is_team,
            "text": chattext
        })
    
    def t(self, key: str, **kwargs) -> str:
        """
        Get a translated string by key.
        
        Args:
            key: Dot-separated key path (e.g., "commands.fishing.cast_success_fish")
            **kwargs: Format arguments for string interpolation
            
        Returns:
            Translated string
        """
        return self._localization.get_string(key, language=self.get_request_language(), **kwargs)


# Create Flask app
app = Flask(__name__)
bot_server = None


@app.route('/process_message', methods=['POST'])
def process_message():
    """Handle incoming messages from the client."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({"error": "No data provided"}), 400
            
        is_team = data.get('is_team', False)
        playername = data.get('playername', '')
        chattext = data.get('chattext', '')
        platform = data.get('platform', 'unknown')
        language = data.get('language', 'en_US')  # Get language from request, default to English
        
        bot_server.logger.info(f"DEBUG: Received language from request: {language}")
        
        if not playername or not chattext:
            return jsonify({"error": "Missing required fields"}), 400
        
        # Store platform info on the bot server for commands to access
        bot_server.platform = platform
        
        # Get preferred identifier (Discord if linked, otherwise original)
        account_linking = bot_server.modules.get_module("account_linking")
        if account_linking:
            playername = account_linking.get_preferred_identifier(platform, playername)
            
        # Process the message with the specified language
        responses = bot_server.process_message(is_team, playername, chattext, language=language)
        
        return jsonify({"responses": responses}), 200
        
    except Exception as e:
        app.logger.error(f"Error processing message: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint."""
    return jsonify({"status": "ok"}), 200


def run_server(host='127.0.0.1', port=8080):
    """Run the Flask server.
    
    Args:
        host: Host address
        port: Port number
    """
    global bot_server
    bot_server = BotServer()
    app.logger.info(f"Starting bot server on {host}:{port} (language: per-request, default: en_US)")
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    run_server()

