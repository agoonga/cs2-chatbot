import os
import logging  # Import the logging module
from time import sleep
import win32gui
import keyboard
import threading
from PyQt6.QtCore import QTimer  # Import QTimer
import sys

from util.config import load_config, copy_files_to_appdata
from util.commands import command_registry
from util.module_registry import module_registry
from util.chat_utils import write_chat_to_cfg, load_chat, send_chat
import util.keys as keys


def resource_path(relative_path):
    """Get the absolute path to a resource, works for PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores files there
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), relative_path)


class Bot:
    def __init__(self, ui_instance) -> None:
        """Initialize the bot with configuration, commands, and chat queue."""
        self.ui_instance = ui_instance  # Store the UI instance
        self.ui_instance.update_status("Initializing bot...")
        self.state = "Initializing..."  # Initialize the state
        # Set up logging
        self.logger = logging.getLogger(__name__)  # Create a logger for the Bot class
        self.logger.setLevel(logging.INFO)  # Set the logging level to INFO

        # File handler for logging to a file
        file_handler = logging.FileHandler("bot.log")
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

        self.chat_queue = []  # Queue to store chat messages to be sent
        self.chat_queue_lock = threading.Lock()  # Lock for thread-safe access to the chat queue
        self.chat_queue_thread = threading.Thread(target=self._chat_queue_worker, daemon=True)
        self.stop_event = threading.Event()  # Event to signal when the bot should stop

        self.config = load_config()  # Load configuration from config.toml
        self.prefix = self.config.get("command_prefix", "@")  # Command prefix (e.g., "@")
        self.load_chat_key = self.config.get("load_chat_key", "kp_1")  # Key to load chat
        self.load_chat_key_win32 = keys.KEYS[self.load_chat_key]  # Win32 key code for load chat key
        self.send_chat_key = self.config.get("send_chat_key", "kp_2")  # Key to send chat
        self.send_chat_key_win32 = keys.KEYS[self.send_chat_key]  # Win32 key code for send chat key
        self.console_log_path = self.config.get("console_log_path")  # Path to the console log file
        self.exec_path = self.config.get("exec_path")  # Path to the chat configuration file
        self.commands = command_registry  # Command registry to manage commands
        self.commands.set_logger(self.logger)
        self.modules = module_registry # Module registry to manage modules
        self.modules.set_logger(self.logger)
        self.paused = False  # Add a paused attribute
        self.running = True  # Add a running flag to control the main loop
        self.stop_event = threading.Event()  # Event to signal when the bot should stop

        # Set up keybinds for pause and resume buttons
        pause_buttons = self.config.get("pause_buttons", "tab,b,y,u").split(",")
        resume_buttons = self.config.get("resume_buttons", "enter,esc").split(",")

        for button in pause_buttons:
            keyboard.add_hotkey(button.strip(), self.set_paused, args=(True,))
        for button in resume_buttons:
            keyboard.add_hotkey(button.strip(), self.set_paused, args=(False,))


    def stop(self):
        """Stop the bot and clean up resources."""
        self.logger.info("Stopping bot...")
        self.stop_event.set()  # Signal all threads to stop sleeping
        try:
            # Schedule the label update on the main thread using QTimer
            QTimer.singleShot(0, lambda: self.ui_instance.update_status("Stopping..."))
        except RuntimeError:
            # Silently ignore if the UI is not running
            pass
        self.running = False  # Set the running flag to False to exit the loop
        keyboard.unhook_all_hotkeys()
        self.logger.info("Bot stopped.")

    def load_commands(self):
        """Load commands from the 'cmds' directory."""
        commands_dir = resource_path("cmds")
        self.commands.load_commands(commands_dir)
        self.logger.info(f"Loaded {len(self.commands)} commands from {commands_dir}")

    def load_modules(self):
        """Load modules from the 'modules' directory."""
        modules_dir = resource_path("modules")
        print(f"Resolved modules directory: {modules_dir}")
        if not os.path.exists(modules_dir):
            print(f"Modules directory does not exist: {modules_dir}")
            return
        self.modules.load_modules(modules_dir)
        self.logger.info(f"Loaded {len(self.modules)} modules from {modules_dir}")

    def reload_commands(self, command_names=None):
        """Reload specific commands or all commands if no names are provided."""
        try:
            if command_names is None:
                # Reload all commands
                self.commands.commands.clear()
                self.load_commands()
                self.logger.info("All commands reloaded successfully.")
            else:
                # Reload specific commands
                if isinstance(command_names, str):
                    command_names = [command_names]  # Convert single string to list

                for command_name in command_names:
                    if command_name in self.commands.commands:
                        del self.commands.commands[command_name]
                        self.logger.info(f"Command '{command_name}' removed.")
                    else:
                        self.logger.warning(f"Command '{command_name}' not found.")
                self.load_commands()
                self.logger.info(f"Specific commands reloaded: {', '.join(command_names)}")
        except Exception as e:
            self.logger.error(f"Failed to reload commands: {e}")

    def reload_modules(self, module_names=None):
        """Reload specific modules or all modules if no names are provided."""
        try:
            if module_names is None:
                # Reload all modules
                self.modules.modules.clear()
                self.load_modules()
                self.logger.info("All modules reloaded successfully.")
            else:
                # Reload specific modules
                if isinstance(module_names, str):
                    module_names = [module_names]  # Convert single string to list

                for module_name in module_names:
                    if module_name in self.modules.modules:
                        del self.modules.modules[module_name]
                        self.logger.info(f"Module '{module_name}' removed.")
                    else:
                        self.logger.warning(f"Module '{module_name}' not found.")
                self.load_modules()
                self.logger.info(f"Specific modules reloaded: {', '.join(module_names)}")
        except Exception as e:
            self.logger.error(f"Failed to reload modules: {e}")

    def connect_to_cs2(self):
        """Connect to the Counter-Strike 2 window."""
        self.logger.info("Waiting for Counter-Strike 2 window...")
        self.ui_instance.update_status("Waiting for CS2 to open...")
        cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")  # Find the CS2 window

        # Wait for the CS2 window to appear
        while cs2_hwnd == 0 and not self.stop_event.is_set():
            cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
            self._interruptible_sleep(0.5)
            
        win32gui.SetForegroundWindow(cs2_hwnd)  # Bring the CS2 window to the foreground
        self.logger.info("Connected to Counter-Strike 2 window.")

    def add_to_chat_queue(self, is_team: bool, chattext: str) -> None:
        """Add a message to the chat queue."""
        # clean message
        chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "י").strip()
        self.logger.debug(f"Adding message to chat queue: {chattext} (team: {is_team})")
        self.chat_queue.append((is_team, chattext))  # Append the message to the queue
        self.logger.info(f"{len(self.chat_queue)} messages in queue.")
        self.logger.info(self.chat_queue)
        self.ui_instance.update_status(f"{self.state} ({len(self.chat_queue)} msgs in queue)")


    def _chat_queue_worker(self) -> None:
        """Process the chat queue."""
        while True:
            while not self.chat_queue and not self.stop_event.is_set():
                self._interruptible_sleep(0.1)
            self.logger.info(f"{len(self.chat_queue)} messages in queue.")
            self.logger.info(self.chat_queue)
            self.ui_instance.update_status(f"{self.state} ({len(self.chat_queue)} msgs in queue)")
            is_team, chattext = self.chat_queue.pop(0)
            self.logger.info(f"Processing chat message: {chattext} (team: {is_team})")

            try:
                # Write the message to the chat configuration file
                write_chat_to_cfg(self.exec_path, self.send_chat_key, is_team, chattext)
                self._interruptible_sleep(0.5)

                # Load the chat message into the game
                while self.paused and not self.stop_event.is_set():
                    self._interruptible_sleep(0.1)

                load_chat(self.load_chat_key_win32)
                self._interruptible_sleep(0.5)

                # Send the chat message
                while self.paused and not self.stop_event.is_set():
                    self._interruptible_sleep(0.1)

                send_chat(self.send_chat_key_win32)
                self._interruptible_sleep(0.5)
            except Exception as e:
                # self.logger.error(f"Error processing chat message: {e}")
                pass
            self.ui_instance.update_status(f"{self.state}")

    def set_paused(self, paused: bool) -> None:
        """Set the paused state of the bot."""
        self.paused = paused
        self.state = "Paused" if paused else "Ready"
        self.logger.info(f"Bot {self.state.lower()}.")
        self.ui_instance.update_status(self.state)  # Update the status
        self.logger.info(f"Status updated to: {self.state}")

    def run(self):
        """Main loop to monitor the console log and process commands."""
        self.logger.info("Starting bot main loop...")
        if not os.path.exists(self.console_log_path):
            self.logger.error(f"Console log file {self.console_log_path} does not exist.")
            raise FileNotFoundError(f"Console log file {self.console_log_path} does not exist.")
        
        if hasattr(sys, '_MEIPASS'):
            copy_files_to_appdata()
            
        # Load commands and modules
        self.load_commands()
        self.logger.info("Commands loaded.")
        self.load_modules()
        self.logger.info("Modules loaded.")

        self.logger.info("Commands and modules loaded.")
        # Connect to the Counter-Strike 2 game window
        self.connect_to_cs2()
        self.chat_queue_thread.start()  # Start the chat queue processing thread
        self.ui_instance.update_status("Ready")
        self.state = "Ready"  # Update the state to "Ready"

        with open(self.console_log_path, "r", encoding="utf-8") as log_file:
            log_file.seek(0, os.SEEK_END)  # Move to the end of the file

            while self.running:  # Check the running flag in the loop
                line = log_file.readline()
                if not line:
                    continue

                # Parse the line to extract playername, is_team, and chattext
                is_team, playername, chattext = self.parse_chat_line(line)
                if not playername or not chattext:
                    continue  # Skip invalid lines silently

                # Pass the parsed arguments to all modules that are reading input
                for module_name, module_instance in self.modules.modules.items():
                    # Check if the module has a `process` method and is reading input
                    if hasattr(module_instance, "process") and getattr(module_instance, "reading_input", True):
                        try:
                            response = module_instance.process(playername, is_team, chattext)
                            if response:
                                self.add_to_chat_queue(is_team, response)
                        except Exception as e:
                            self.logger.error(f"Error in module '{module_name}' while processing line: {e}")

                # Process commands if the line contains the command prefix
                if chattext.startswith(self.prefix):
                    try:
                        command_name = chattext[len(self.prefix):].split(" ")[0]
                        command_args = chattext[len(self.prefix) + len(command_name):].strip()

                        if command_name in self.commands.commands:
                            self.logger.info(f"Executing command: {command_name} with args: {command_args}")
                            self.commands.execute(command_name, self, is_team, playername, command_args)
                        else:
                            self.logger.warning(f"Unknown command: {command_name}")
                    except Exception as e:
                        self.logger.error(f"Error executing command: {line}\n{e}")


        self.logger.info("Bot main loop exited.")

    def parse_chat_line(self, line: str):
        """Parse a chat line to extract the player name, team status, and chat text."""
        try:
            # Determine if the message is a team message
            is_team = line.split("] ")[0].split("  [")[1] != "ALL"

            # Extract the player name and chat text
            chatline = line.split("] ", 1)[1].rsplit(": ", 1)  # Use rsplit to split at the last occurrence of ": "
            playername = chatline[0].strip().replace("\u200e", "")
            playername = playername.split("\ufe6b")[0].split("[DEAD]")[0].strip()
            playername = playername.replace("/", "/​").replace("'", "י")

            # Extract and sanitize the chat text
            chattext = chatline[1].strip()
            chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "י").strip()

            return is_team, playername, chattext
        except (ValueError, IndexError):
            # Silently ignore invalid chat lines
            return None, None, None

    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep for the specified duration, but wake up if stop_event is set."""
        interval = 0.1  # Check every 0.1 seconds
        elapsed = 0
        while elapsed < duration:
            if self.stop_event.is_set():
                break
            sleep(interval)
            elapsed += interval