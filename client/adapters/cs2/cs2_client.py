import os
import logging
import sys
import threading
import win32gui
import keyboard
import requests
from time import sleep
from typing import Optional, Tuple

from util.config import load_config
from util.chat_utils import write_chat_to_cfg, load_chat, send_chat
import util.keys as keys


class CS2Client:
    """Client adapter for Counter-Strike 2 that handles game-specific interactions."""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080") -> None:
        """Initialize the CS2 client adapter."""
        # Remove trailing slash if present
        self.server_url = server_url.rstrip('/')
        self.state = "Initializing..."
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # File handler for logging to a file
        file_handler = logging.FileHandler("cs2_client.log")
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        
        # Stream handler for logging to the console
        console_handler = logging.StreamHandler(stream=open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1))
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        console_handler.setFormatter(console_formatter)
        
        # Add both handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
        
        # Load configuration
        self.config = load_config()
        self.load_chat_key = self.config.get("load_chat_key", "kp_1")
        self.load_chat_key_win32 = keys.KEYS[self.load_chat_key]
        self.send_chat_key = self.config.get("send_chat_key", "kp_2")
        self.send_chat_key_win32 = keys.KEYS[self.send_chat_key]
        self.console_log_path = self.config.get("console_log_path")
        self.exec_path = self.config.get("exec_path")
        
        # Chat queue for outgoing messages
        self.chat_queue = []
        self.chat_queue_lock = threading.Lock()
        self.chat_queue_thread = threading.Thread(target=self._chat_queue_worker, daemon=True)
        
        # Control flags
        self.paused = False
        self.running = True
        self.stop_event = threading.Event()
        
    def stop(self):
        """Stop the client and clean up resources."""
        self.logger.info("Stopping CS2 client...")
        self.stop_event.set()
        self.running = False
        keyboard.unhook_all_hotkeys()
        self.logger.info("CS2 client stopped.")
        
    def connect_to_cs2(self):
        """Connect to the Counter-Strike 2 window."""
        self.logger.info("Waiting for Counter-Strike 2 window...")
        cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        
        # Wait for the CS2 window to appear
        while cs2_hwnd == 0 and not self.stop_event.is_set():
            cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
            self._interruptible_sleep(0.5)
            
        if cs2_hwnd != 0:
            win32gui.SetForegroundWindow(cs2_hwnd)
            self.logger.info("Connected to Counter-Strike 2 window.")
        
    def add_to_chat_queue(self, is_team: bool, chattext: str) -> None:
        """Add a message to the chat queue."""
        # Clean message
        chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "ʹ").replace("\"", "ʺ").strip()
        if not chattext:
            return
            
        # Check if a duplicate message is already in the queue
        with self.chat_queue_lock:
            for queued_is_team, queued_chattext in self.chat_queue:
                if queued_chattext == chattext and queued_is_team == is_team:
                    self.logger.debug(f"Duplicate message found in queue: {chattext} (team: {is_team})")
                    return
                    
        self.logger.debug(f"Adding message to chat queue: {chattext} (team: {is_team})")
        self.chat_queue.append((is_team, chattext))
        self.logger.info(f"{len(self.chat_queue)} messages in queue.")
        
    def _chat_queue_worker(self) -> None:
        """Process the chat queue and send messages to CS2."""
        while True:
            while not self.chat_queue and not self.stop_event.is_set():
                self._interruptible_sleep(0.1)
                
            if not self.chat_queue:
                continue
                
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
                self.logger.error(f"Error processing chat message: {e}")
                
    def set_paused(self, paused: bool) -> None:
        """Set the paused state of the client."""
        self.paused = paused
        self.state = "Paused" if paused else "Ready"
        self.logger.info(f"CS2 client {self.state.lower()}.")
        
    def parse_chat_line(self, line: str) -> Tuple[Optional[bool], Optional[str], Optional[str]]:
        """Parse a chat line to extract the player name, team status, and chat text."""
        try:
            # Determine if the message is a team message
            is_team = line.split("] ")[0].split("  [")[1] != "ALL"
            
            # Extract the player name and chat text
            chatline = line.split("] ", 1)[1].rsplit(": ", 1)
            playername = chatline[0].strip().replace("\u200e", "")
            playername = playername.split("\ufe6b")[0].split("[DEAD]")[0].strip()
            playername = playername.replace("/", "/​").replace("'", "י")
            
            # Extract and sanitize the chat text
            chattext = chatline[1].strip()
            chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "י").strip()
            
            return is_team, playername, chattext
        except (ValueError, IndexError):
            # Silently ignore invalid chat lines
            return None, None, None
            
    def send_to_server(self, is_team: bool, playername: str, chattext: str) -> Optional[list]:
        """Send a message to the server and get responses."""
        from time import time
        start_time = time()
        
        try:
            url = f"{self.server_url}/process_message"
            self.logger.info(f"Sending POST to: {url}")
            self.logger.info(f"Payload: is_team={is_team}, playername={playername}, chattext={chattext}")
            
            request_start = time()
            response = requests.post(
                url,
                json={
                    "is_team": is_team,
                    "playername": playername,
                    "chattext": chattext,
                    "platform": "cs2"
                },
                timeout=5
            )
            request_time = time() - request_start
            
            self.logger.info(f"Response status: {response.status_code} (request took {request_time:.4f}s)")
            
            if response.status_code == 200:
                data = response.json()
                total_time = time() - start_time
                self.logger.info(f"Total send_to_server time: {total_time:.4f}s")
                return data.get("responses", [])
            else:
                self.logger.error(f"Server returned status code: {response.status_code}, URL was: {url}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to communicate with server: {e}, URL was: {url}")
            return None
            
    def run(self):
        """Main loop to monitor the console log and process messages."""
        if not os.path.exists(self.console_log_path):
            self.logger.error(f"Console log file {self.console_log_path} does not exist.")
            return
            
        # Connect to CS2 window
        self.connect_to_cs2()
        
        # Start chat queue worker
        self.chat_queue_thread.start()
        
        # Set up keybinds
        pause_buttons = self.config.get("pause_buttons", "tab,b,p").split(",")
        resume_buttons = self.config.get("resume_buttons", "enter,esc").split(",")
        
        self.logger.info("Registering hotkeys...")
        
        try:
            for button in pause_buttons:
                button = button.strip()
                if button:
                    self.logger.info(f"Registering pause hotkey: {button}")
                    keyboard.add_hotkey(button, self.set_paused, args=(True,))
                    
            for button in resume_buttons:
                button = button.strip()
                if button:
                    self.logger.info(f"Registering resume hotkey: {button}")
                    keyboard.add_hotkey(button, self.set_paused, args=(False,))
                    
            self.logger.info("Hotkeys registered successfully.")
        except Exception as e:
            self.logger.error(f"Failed to register hotkeys: {e}")
            
        self.state = "Ready"
        
        # Open console log file
        self.logger.info("Attempting to read console log...")
        try:
            log_file = open(self.console_log_path, "r", encoding="utf-8", errors="ignore")
        except FileNotFoundError:
            self.logger.error(f"Console log file {self.console_log_path} not found.")
            return
            
        log_file.seek(0, os.SEEK_END)  # Move to the end of the file
        
        self.logger.info("Starting CS2 client main loop...")
        while self.running:
            line = log_file.readline()
            if not line:
                continue
                
            # Parse the line
            is_team, playername, chattext = self.parse_chat_line(line)
            if not playername or not chattext:
                continue
            
            self.logger.info(f"Parsed chat: [{playername}] {chattext} (team: {is_team})")
                
            # Send to server for processing
            responses = self.send_to_server(is_team, playername, chattext)
            
            # Queue responses for sending to CS2
            if responses:
                for response in responses:
                    response_is_team = response.get("is_team", is_team)
                    response_text = response.get("text", "")
                    if response_text:
                        self.add_to_chat_queue(response_is_team, response_text)
                        
        self.logger.info("CS2 client main loop exited.")
        
    def _interruptible_sleep(self, duration: float) -> None:
        """Sleep for the specified duration, but wake up if stop_event is set."""
        interval = 0.1
        elapsed = 0
        while elapsed < duration:
            if self.stop_event.is_set():
                break
            sleep(interval)
            elapsed += interval
