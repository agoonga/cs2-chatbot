import os
from time import sleep
import win32gui

from util.config import load_config
from util.commands import CommandRegistry
from util.module_registry import ModuleRegistry
from util.chat_utils import write_chat_to_cfg, load_chat, send_chat
import util.keys as keys


class Bot:
    def __init__(self) -> None:
        """Initialize the bot with configuration, commands, and chat queue."""
        self.chat_queue = []  # Queue to store chat messages to be sent
        self.config = load_config()  # Load configuration from config.toml
        self.prefix = self.config.get("command_prefix", "@")  # Command prefix (e.g., "@")
        self.load_chat_key = self.config.get("load_chat_key", "kp_1")  # Key to load chat
        self.load_chat_key_win32 = keys.KEYS[self.load_chat_key]  # Win32 key code for load chat key
        self.send_chat_key = self.config.get("send_chat_key", "kp_2")  # Key to send chat
        self.send_chat_key_win32 = keys.KEYS[self.send_chat_key]  # Win32 key code for send chat key
        self.console_log_path = self.config.get("console_log_path")  # Path to the console log file
        self.exec_path = self.config.get("exec_path")  # Path to the chat configuration file
        self.commands = CommandRegistry()  # Command registry to manage commands
        self.modules = ModuleRegistry()  # Module registry to manage modules

        # Load commands from the "cmds" directory
        commands_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cmds")
        self.commands.load_commands(commands_dir)

        # Load modules from the "modules" directory
        modules_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "modules")
        self.modules.load_modules(modules_dir)

        # Connect to the Counter-Strike 2 game window
        self.connect_to_cs2()

    def connect_to_cs2(self):
        """Connect to the Counter-Strike 2 window."""
        cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")  # Find the CS2 window
        if cs2_hwnd == 0:
            raise Exception("Counter-Strike 2 is not running.")  # Raise an error if the game is not running
        win32gui.SetForegroundWindow(cs2_hwnd)  # Bring the CS2 window to the foreground

    def add_to_chat_queue(self, is_team: bool, chattext: str) -> None:
        """Add a message to the chat queue."""
        self.chat_queue.append((is_team, chattext))  # Append the message to the queue

    def run_chat_queue(self) -> None:
        """Process the chat queue."""
        if self.chat_queue:
            # Get the next message from the queue
            is_team, chattext = self.chat_queue.pop(0)

            # Write the message to the chat configuration file
            write_chat_to_cfg(self.exec_path, self.send_chat_key, is_team, chattext)
            sleep(0.5)

            # Load the chat message into the game
            load_chat(self.load_chat_key_win32)
            sleep(0.5)

            # Send the chat message
            send_chat(self.send_chat_key_win32)
            sleep(0.5)

            # Process the next message in the queue
            self.run_chat_queue()

    def run(self):
        """Main loop to monitor the console log and process commands."""
        if not os.path.exists(self.console_log_path):
            raise FileNotFoundError(f"Console log file {self.console_log_path} does not exist.")  # Ensure the log file exists

        with open(self.console_log_path, "r", encoding="utf-8") as log_file:
            # Move to the end of the file to start monitoring new lines
            log_file.seek(0, os.SEEK_END)

            while True:
                # Read the next line from the log file
                line = log_file.readline()
                if not line:
                    sleep(0.1)  # Wait briefly if no new line is available
                    continue

                # Process lines containing the command prefix
                if self.prefix in line:
                    try:
                        # Parse the player name, team status, and chat text
                        is_team, playername, chattext = self.parse_chat_line(line)

                        # Check if the chat text starts with the command prefix
                        if chattext.startswith(self.prefix):
                            # Extract the command name and arguments
                            command_name = chattext[len(self.prefix):].split(" ")[0]
                            command_args = chattext[len(self.prefix) + len(command_name):].strip()

                            # Execute the command if it is registered
                            if command_name in self.commands.commands:
                                self.commands.execute(command_name, self, is_team, playername, command_args)
                            else:
                                print(f"Unknown command: {command_name}")  # Print a message for unknown commands
                    except ValueError as e:
                        print(f"Error processing line: {line}\n{e}")  # Handle errors gracefully

                # Process the chat queue
                self.run_chat_queue()

    def parse_chat_line(self, line: str):
        """Parse a chat line to extract the player name, team status, and chat text."""
        try:
            # Determine if the message is a team message
            is_team = line.split("] ")[0].split("  [")[1] != "ALL"

            # Extract the player name and chat text
            chatline = line.split("] ")[1].split(": ")
            playername = chatline[0].strip().replace("\u200e", "")
            playername = playername.split("\ufe6b")[0].split("[DEAD]")[0].strip()
            playername = playername.replace("/", "/​").replace("'", "י")

            # Extract and sanitize the chat text
            chattext = chatline[1].strip()
            chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "י").strip()

            return is_team, playername, chattext
        except (ValueError, IndexError) as e:
            raise ValueError(f"Invalid chat line format: {line}") from e