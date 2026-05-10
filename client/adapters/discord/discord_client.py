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
        
        # Load configuration
        self.config = load_config()
        self.discord_token = os.getenv('DISCORD_BOT_TOKEN') or self.config.get('discord_bot_token')
        raw_discord_prefix = self.config.get('discord_command_prefix', self.config.get('command_prefix', '@'))
        self.command_prefixes = self._parse_prefixes(raw_discord_prefix)
        
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
        
        # Check if the message starts with any configured command prefix
        if not any(chattext.startswith(prefix) for prefix in self.command_prefixes):
            return
        
        # Extract playername (use Discord username, not display name)
        playername = str(message.author.name)
        is_team = isinstance(message.channel, discord.DMChannel)
        
        self.logger.info(f"Received message from {playername}: {chattext} (DM: {is_team})")
        
        # Send to server for processing
        responses = await self.send_to_server(is_team, playername, chattext)
        
        # Send responses back to Discord
        if responses:
            for response in responses:
                response_text = response.get("text", "")
                if response_text:
                    try:
                        await message.channel.send(response_text)
                    except discord.errors.HTTPException as e:
                        self.logger.error(f"Failed to send message: {e}")
    
    async def send_to_server(self, is_team: bool, playername: str, chattext: str) -> Optional[List[Dict]]:
        """Send a message to the server and get responses."""
        try:
            url = f"{self.server_url}/process_message"
            self.logger.info(f"Sending POST to: {url}")
            self.logger.info(f"Payload: is_team={is_team}, playername={playername}, chattext={chattext}")
            
            # Get language from adapter config
            language = self.config.get("adapters", {}).get("discord", {}).get("language", "en_US")
            
            response = requests.post(
                url,
                json={
                    "is_team": is_team,
                    "playername": playername,
                    "chattext": chattext,
                    "platform": "discord",
                    "language": language
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
