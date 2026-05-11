import os
import logging
import threading
import atexit
import re
import uuid
import toml
import win32gui
import keyboard
import requests
import msvcrt
from time import sleep
from typing import Optional, Tuple, List

from util.config import load_config, get_config_path
from util.chat_utils import write_chat_to_cfg, load_chat, send_chat
import util.keys as keys


class CS2Client:
    """Client adapter for Counter-Strike 2 that handles game-specific interactions."""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080") -> None:
        """Initialize the CS2 client adapter."""
        self._instance_lock_handle = None
        self._instance_lock_path = None

        # Prevent multiple CS2 client processes from running at the same time.
        if not self._acquire_instance_lock():
            raise RuntimeError("Another CS2 client instance is already running.")

        atexit.register(self._release_instance_lock)

        # Remove trailing slash if present
        self.server_url = server_url.rstrip('/')
        self.state = "Initializing..."
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        
        # File and console handlers (only once for this logger).
        if not self.logger.handlers:
            file_handler = logging.FileHandler("cs2_client.log")
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            file_handler.setFormatter(file_formatter)

            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            console_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
            console_handler.setFormatter(console_formatter)

            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
        
        # Load configuration
        self.config = load_config()
        configured_language = self.config.get("adapters", {}).get("cs2", {}).get("language", "en_US")
        self.language = self._normalize_language_input(configured_language) or "en_US"
        self.session_id = f"cs2-{uuid.uuid4().hex}"
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
        self.logger.info(f"CS2 session initialized: {self.session_id}")

    def _acquire_instance_lock(self) -> bool:
        """Acquire a process lock to ensure only one CS2 client instance runs."""
        lock_dir = os.path.dirname(get_config_path())
        lock_path = os.path.join(lock_dir, "cs2_client.lock")
        os.makedirs(lock_dir, exist_ok=True)

        try:
            handle = open(lock_path, "a+")
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            self._instance_lock_handle = handle
            self._instance_lock_path = lock_path
            return True
        except OSError:
            return False

    def _release_instance_lock(self) -> None:
        """Release the process lock if held by this instance."""
        if not self._instance_lock_handle:
            return

        try:
            self._instance_lock_handle.seek(0)
            msvcrt.locking(self._instance_lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        finally:
            try:
                self._instance_lock_handle.close()
            except OSError:
                pass
            self._instance_lock_handle = None

    def _parse_prefixes(self):
        """Normalize configured command prefixes into a list."""
        raw_prefixes = self.config.get("command_prefix", "@")
        if isinstance(raw_prefixes, list):
            prefixes = [str(p).strip() for p in raw_prefixes if str(p).strip()]
            return prefixes or ["@"]

        if isinstance(raw_prefixes, str):
            prefixes = [p.strip() for p in raw_prefixes.split(",") if p.strip()]
            return prefixes or ["@"]

        return ["@"]

    def _candidate_prefixes(self) -> List[str]:
        """Return configured prefixes plus common defaults for robustness."""
        prefixes = self._parse_prefixes()
        for fallback in ["!", "@"]:
            if fallback not in prefixes:
                prefixes.append(fallback)
        return prefixes

    def _extract_local_command(self, chattext: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """Extract prefix, command name, and args from a local command string."""
        if not chattext:
            return None, None, []

        # CS2 logs can include invisible direction marks and zero-width chars.
        normalized = chattext.strip()
        normalized = normalized.replace("\u200b", "")
        normalized = normalized.lstrip("\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e")

        # parse_chat_line currently sanitizes slashes as "/\u200b"; undo it here for local command matching.
        normalized = normalized.replace("/\u200b", "/")

        # Some users type slash-prefixed commands in chat; support both `!lang` and `/!lang`.
        if normalized.startswith("/"):
            normalized = normalized[1:].lstrip(" \t\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e")

        matched_prefix = None
        for prefix in self._candidate_prefixes():
            if normalized.startswith(prefix):
                matched_prefix = prefix
                break

        if not matched_prefix:
            return None, None, []

        remainder = normalized[len(matched_prefix):].strip()
        if not remainder:
            return matched_prefix, None, []

        parts = remainder.split()
        if not parts:
            return matched_prefix, None, []

        return matched_prefix, parts[0].lower(), parts[1:]

    def _normalize_language_input(self, value: str) -> Optional[str]:
        """Map user input to supported language code."""
        if not value:
            return None

        key = value.strip().lower().replace("-", "_")
        aliases = {
            "en_us": "en_US",
            "en": "en_US",
            "eng": "en_US",
            "english": "en_US",
            "en_sg": "en_SG",
            "ensg": "en_SG",
            "sg": "en_SG",
            "singapore": "en_SG",
            "singaporean": "en_SG",
            "pt_br": "pt_BR",
            "pt": "pt_BR",
            "ptbr": "pt_BR",
            "portuguese": "pt_BR",
            "portugues": "pt_BR",
            "br": "pt_BR",
            "brazil": "pt_BR",
            "es_es": "es_ES",
            "es": "es_ES",
            "esp": "es_ES",
            "spanish": "es_ES",
            "fr_fr": "fr_FR",
            "fr": "fr_FR",
            "french": "fr_FR",
            "de_de": "de_DE",
            "de": "de_DE",
            "ger": "de_DE",
            "german": "de_DE",
            "it_it": "it_IT",
            "it": "it_IT",
            "ita": "it_IT",
            "italian": "it_IT",
            "nl_nl": "nl_NL",
            "nl": "nl_NL",
            "dutch": "nl_NL",
            "ru_ru": "ru_RU",
            "ru": "ru_RU",
            "russian": "ru_RU",
            "ja_jp": "ja_JP",
            "ja": "ja_JP",
            "jp": "ja_JP",
            "japanese": "ja_JP",
            "tr_tr": "tr_TR",
            "tr": "tr_TR",
            "tur": "tr_TR",
            "turkish": "tr_TR",
            "turkce": "tr_TR",
            "türkçe": "tr_TR",
            "sv_se": "sv_SE",
            "sv": "sv_SE",
            "swe": "sv_SE",
            "swedish": "sv_SE",
            "svenska": "sv_SE",
            "ko_kr": "ko_KR",
            "ko": "ko_KR",
            "kor": "ko_KR",
            "korean": "ko_KR",
            "zh_cn": "zh_CN",
            "zh": "zh_CN",
            "cn": "zh_CN",
            "chinese": "zh_CN",
            "mandarin": "zh_CN",
            "hi_in": "hi_IN",
            "hi": "hi_IN",
            "hindi": "hi_IN",
            "india": "hi_IN",
            "polish": "pl_PL",
            "pl_pl": "pl_PL",
            "pl": "pl_PL",
            "pol": "pl_PL",
        }
        return aliases.get(key)

    def _persist_language(self, language_code: str) -> None:
        """Persist CS2 adapter language to config.toml."""
        config_path = get_config_path()
        config_data = load_config()
        adapters = config_data.setdefault("adapters", {})
        cs2_config = adapters.setdefault("cs2", {})
        cs2_config["language"] = language_code

        with open(config_path, "w", encoding="utf-8") as f:
            toml.dump(config_data, f)

        # Keep runtime config in sync without requiring restart.
        self.config = config_data
        self.language = language_code

    def _handle_local_language_command(self, is_team: bool, chattext: str) -> bool:
        """Handle local !lang/@lang command in adapter; returns True when consumed."""
        matched_prefix, command_name, args = self._extract_local_command(chattext)
        if not matched_prefix or not command_name:
            return False

        if command_name not in ["lang", "language"]:
            return False

        # Show current language if no argument provided.
        current = self.language
        if not args:
            self.add_to_chat_queue(is_team, f"Language is currently {current}. Usage: {matched_prefix}lang <code>")
            return True

        requested = args[0]
        normalized = self._normalize_language_input(requested)
        if not normalized:
            self.add_to_chat_queue(
                is_team,
                "Unknown language. Try: en_US, en_SG, pt_BR, es_ES, fr_FR, de_DE, it_IT, nl_NL, ru_RU, ja_JP, tr_TR, sv_SE, ko_KR, pl_PL, zh_CN, hi_IN",
            )
            return True

        self._persist_language(normalized)
        self.add_to_chat_queue(is_team, f"Language changed to {normalized}.")
        self.logger.info(f"CS2 adapter language changed locally to {normalized}")
        return True
        
    def stop(self):
        """Stop the client and clean up resources."""
        self.logger.info("Stopping CS2 client...")
        self.stop_event.set()
        self.running = False
        keyboard.unhook_all_hotkeys()
        self._release_instance_lock()
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

    def remove_player_from_chat_queue(self, playername: str) -> int:
        """Remove queued bot responses that belong to a specific player."""
        normalized_player = (playername or "").strip()
        if not normalized_player:
            return 0

        prefix = f"{normalized_player}:"
        with self.chat_queue_lock:
            before = len(self.chat_queue)
            self.chat_queue = [item for item in self.chat_queue if not item[1].startswith(prefix)]
            removed = before - len(self.chat_queue)

        if removed > 0:
            self.logger.info(f"Removed {removed} queued messages for player {normalized_player}.")
        return removed
        
    def _chat_queue_worker(self) -> None:
        """Process the chat queue and send messages to CS2."""
        while True:
            while not self.chat_queue and not self.stop_event.is_set():
                self._interruptible_sleep(0.1)
                
            if not self.chat_queue:
                continue

            with self.chat_queue_lock:
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
            chatline = line.split("] ", 1)[1].split(": ", 1)
            playername = chatline[0].strip().replace("\u200e", "")
            playername = playername.split("\ufe6b")[0].split("[DEAD]")[0].strip()
            playername = self._repair_console_mojibake(playername)
            playername = playername.replace("/", "/​").replace("'", "י")
            
            # Extract and sanitize the chat text
            chattext = chatline[1].strip()
            chattext = self._repair_console_mojibake(chattext)
            chattext = chattext.replace(";", ";").replace("/", "/​").replace("'", "י").strip()
            chattext = chattext.lstrip("\ufeff\u200b\u200e\u200f\u202a\u202b\u202c\u202d\u202e")
            
            return is_team, playername, chattext
        except (ValueError, IndexError):
            # Silently ignore invalid chat lines
            return None, None, None

    def _repair_console_mojibake(self, text: str) -> str:
        """Attempt to recover UTF-8 text that was mis-decoded as a legacy code page."""
        if not text:
            return text

        # Typical mojibake from UTF-8 Cyrillic appears with box-drawing characters.
        if not re.search(r"[\u2500-\u257F]", text):
            return text

        for source_encoding in ("cp866", "cp437", "cp850", "latin-1"):
            try:
                repaired = text.encode(source_encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

            # Keep the repair only if it actually introduces Cyrillic characters.
            if re.search(r"[\u0400-\u04FF]", repaired):
                return repaired

        return text

    def _is_echoed_bot_message(self, playername: str, chattext: str) -> bool:
        """Detect bot echo lines in console.log and skip sending them back to the server."""
        if not playername or not chattext:
            return False

        normalized_player = playername.strip().rstrip(":")
        normalized_chat = chattext.strip()
        if not normalized_player or not normalized_chat:
            return False

        # Bot responses are typically prefixed with "{player}: ..." in chat output.
        if normalized_chat.startswith(f"{normalized_player}: "):
            return True

        # Defensive: older not-found responses missing player can appear as ": message".
        if normalized_chat.startswith(": "):
            return True

        return False
            
    def send_to_server(self, is_team: bool, playername: str, chattext: str) -> Optional[list]:
        """Send a message to the server and get responses."""
        from time import time
        start_time = time()
        
        try:
            url = f"{self.server_url}/process_message"
            self.logger.info(f"Sending POST to: {url}")
            self.logger.info(f"Payload: is_team={is_team}, playername={playername}, chattext={chattext}")
            
            # Use runtime language to avoid mid-session config drift.
            language = self.language
            self.logger.info(f"DEBUG: Config adapters: {self.config.get('adapters', {})}")
            self.logger.info(f"DEBUG: CS2 config: {self.config.get('adapters', {}).get('cs2', {})}")
            self.logger.info(f"DEBUG: Active runtime language: {language}")
            
            request_start = time()
            response = requests.post(
                url,
                json={
                    "is_team": is_team,
                    "playername": playername,
                    "chattext": chattext,
                    "platform": "cs2",
                    "language": language,
                    "session_id": self.session_id,
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
        pause_buttons = self.config.get("pause_buttons", "tab,b,y,u").split(",")
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
            log_file = open(self.console_log_path, "r", encoding="utf-8")
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

            if self._is_echoed_bot_message(playername, chattext):
                self.logger.debug(f"Skipping echoed bot output: [{playername}] {chattext}")
                continue
            
            self.logger.info(f"Parsed chat: [{playername}] {chattext} (team: {is_team})")

            # Handle adapter-local language command without hitting the server.
            if self._handle_local_language_command(is_team, chattext):
                continue
                
            # Send to server for processing
            responses = self.send_to_server(is_team, playername, chattext)
            
            # Queue responses for sending to CS2
            if responses:
                for response in responses:
                    control = response.get("control")
                    if control == "remove_player_queue":
                        self.remove_player_from_chat_queue(response.get("player", ""))
                        continue

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
