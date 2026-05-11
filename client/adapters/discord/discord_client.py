import os
import logging
import discord
import requests
from discord.ext import commands
from typing import Optional, List, Dict
from dotenv import load_dotenv

from util.config import load_config

# Load environment variables from .env file
load_dotenv()


class DiscordClient(commands.Bot):
    """Client adapter for Discord that handles Discord-specific interactions."""
    
    def __init__(self, server_url: str = "http://127.0.0.1:8080") -> None:
        """Initialize the Discord client adapter."""
        # Discord intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.guilds = True
        intents.members = True
        
        # Initialize the Discord bot
        super().__init__(command_prefix='@', intents=intents)
        
        # Remove trailing slash if present
        self.server_url = server_url.rstrip('/')
        
        # Set up logging
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # File handler for logging to a file
        file_handler = logging.FileHandler("discord_client.log")
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
        self.active_scramble_sessions = set()
        self.channel_languages = {}
        
        # Load configuration
        self.config = load_config()
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN') or self.config.get('discord_bot_token')
        raw_discord_prefix = self.config.get('discord_command_prefix', self.config.get('command_prefix', '@'))
        self.command_prefixes = self._parse_prefixes(raw_discord_prefix)
        configured_language = self.config.get("adapters", {}).get("discord", {}).get("language", "en_US")
        self.default_language = self._normalize_language_input(configured_language) or "en_US"
        
        if not self.discord_token:
            self.logger.error("Discord bot token not found in environment or config!")
            raise ValueError("Discord bot token is required")
        
        self.logger.info(f"Discord client initialized with server URL: {self.server_url}")

    def _parse_prefixes(self, raw_prefixes):
        """Normalize command prefixes from config into a list."""
        if isinstance(raw_prefixes, list):
            prefixes = [str(p).strip() for p in raw_prefixes if str(p).strip()]
            return prefixes or ["@"]

        if isinstance(raw_prefixes, str):
            prefixes = [p.strip() for p in raw_prefixes.split(",") if p.strip()]
            return prefixes or ["@"]

        return ["@"]

    def _candidate_prefixes(self):
        """Return configured prefixes plus common defaults for robustness."""
        prefixes = list(self.command_prefixes)
        for fallback in ["!", "@"]:
            if fallback not in prefixes:
                prefixes.append(fallback)
        return prefixes

    def _normalize_chattext(self, chattext: str) -> str:
        """Normalize chat text for reliable local command detection."""
        normalized = (chattext or "").strip()
        normalized = normalized.replace("\u200b", "")
        normalized = normalized.lstrip("\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e")
        if normalized.startswith("/"):
            normalized = normalized[1:].lstrip(" \t\ufeff\u200e\u200f\u202a\u202b\u202c\u202d\u202e")
        return normalized

    def _extract_local_command(self, chattext: str):
        """Extract prefix, command name, and args from text for local handling."""
        normalized = self._normalize_chattext(chattext)
        if not normalized:
            return None, None, []

        matched_prefix = next((prefix for prefix in self._candidate_prefixes() if normalized.startswith(prefix)), None)
        if not matched_prefix:
            return None, None, []

        remainder = normalized[len(matched_prefix):].strip()
        if not remainder:
            return matched_prefix, None, []

        parts = remainder.split()
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
            "pr": "pt_BR",
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
            "pl_pl": "pl_PL",
            "pl": "pl_PL",
            "pol": "pl_PL",
            "polish": "pl_PL",
        }
        return aliases.get(key)

    async def _handle_local_language_command(self, message: discord.Message, chattext: str, session_id: str) -> bool:
        """Handle !lang/@lang command locally for this channel/session."""
        matched_prefix, command_name, args = self._extract_local_command(chattext)
        if not matched_prefix or not command_name:
            return False

        if command_name not in ["lang", "language"]:
            return False

        current_language = self.channel_languages.get(session_id, self.default_language)
        if len(args) < 1:
            await message.channel.send(
                f"Language for this channel is currently {current_language}. Usage: {matched_prefix}lang <code>"
            )
            return True

        normalized = self._normalize_language_input(args[0])
        if not normalized:
            await message.channel.send(
                "Unknown language. Try: en_US, en_SG, pt_BR, es_ES, fr_FR, de_DE, it_IT, nl_NL, ru_RU, ja_JP, tr_TR, sv_SE, ko_KR, pl_PL, zh_CN, hi_IN"
            )
            return True

        self.channel_languages[session_id] = normalized
        await message.channel.send(f"Language for this channel changed to {normalized}.")
        self.logger.info(f"Discord channel language changed: session={session_id} language={normalized}")
        return True
    
    async def on_ready(self):
        """Called when the bot successfully connects to Discord."""
        self.logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        self.logger.info(f"Connected to {len(self.guilds)} guilds")
        
    async def on_message(self, message: discord.Message):
        """Called when a message is received."""
        # Ignore messages from the bot itself
        if message.author == self.user:
            return
        
        # Process the message
        chattext = message.content.strip()
        if not chattext:
            return
        normalized_chattext = self._normalize_chattext(chattext)
        
        # Extract playername (use Discord username, not display name)
        playername = str(message.author.name)
        is_team = isinstance(message.channel, discord.DMChannel)
        session_id = getattr(message.channel, "name", None) or f"dm-{message.channel.id}"
        is_prefixed = any(normalized_chattext.startswith(prefix) for prefix in self._candidate_prefixes())

        if await self._handle_local_language_command(message, chattext, session_id):
            return

        if not is_prefixed and session_id not in self.active_scramble_sessions:
            return
        
        self.logger.info(f"Received message from {playername}: {chattext} (DM: {is_team})")
        
        # Send to server for processing
        language = self.channel_languages.get(session_id, self.default_language)
        responses = await self.send_to_server(
            is_team,
            playername,
            chattext,
            session_id=session_id,
            language=language,
        )

        if is_prefixed:
            matched_prefix = next((prefix for prefix in self._candidate_prefixes() if normalized_chattext.startswith(prefix)), None)
            command_name = None
            if matched_prefix:
                remainder = normalized_chattext[len(matched_prefix):].strip()
                if remainder:
                    command_name = remainder.split()[0].lower()

            if command_name == "scramble" and responses:
                self.active_scramble_sessions.add(session_id)
        elif responses:
            self.active_scramble_sessions.discard(session_id)
        
        # Send responses back to Discord
        if responses:
            for response in responses:
                response_text = response.get("text", "")
                if response_text:
                    try:
                        await message.channel.send(response_text)
                    except discord.errors.HTTPException as e:
                        self.logger.error(f"Failed to send message: {e}")
    
    async def send_to_server(
        self,
        is_team: bool,
        playername: str,
        chattext: str,
        session_id: Optional[str] = None,
        language: Optional[str] = None,
    ) -> Optional[List[Dict]]:
        """Send a message to the server and get responses."""
        try:
            url = f"{self.server_url}/process_message"
            self.logger.info(f"Sending POST to: {url}")
            resolved_language = language or self.default_language
            self.logger.info(
                f"Payload: is_team={is_team}, playername={playername}, chattext={chattext}, session_id={session_id}, language={resolved_language}"
            )
            
            response = requests.post(
                url,
                json={
                    "is_team": is_team,
                    "playername": playername,
                    "chattext": chattext,
                    "platform": "discord",
                    "language": resolved_language,
                    "session_id": session_id or "discord-default",
                },
                timeout=5
            )
            
            self.logger.info(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                return data.get("responses", [])
            else:
                self.logger.error(f"Server returned status code: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to communicate with server: {e}")
            return None
    
    def run_bot(self):
        """Run the Discord bot."""
        self.logger.info("Starting Discord client...")
        try:
            self.run(self.discord_token)
        except Exception as e:
            self.logger.error(f"Failed to start Discord client: {e}")
            raise
