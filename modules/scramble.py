import random
import os
import sys

from util.module_registry import module_registry
from modules.economy import Economy

class Scramble:
    load_after = ["economy"]  # Load after the economy module
    def __init__(self):
        self.word_list = self.load_word_list()
        self.games = {}
        self.reading_input = False  # Indicates whether any session is actively processing input
        self.economy: Economy = module_registry.get_module("economy")  # Retrieve the Economy module from the module registry

    def load_word_list(self):
        """
        Load the scramble dictionary from a file.
        """
        appdata_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(appdata_dir, "data", "scramble_dict.txt") if hasattr(sys, '_MEIPASS') else os.path.join("modules", "data", "scramble_dict.txt")
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    def _sync_reading_input(self):
        self.reading_input = bool(self.games)

    def start_new_game(self, session_id: str, is_team: bool):
        """
        Start a new scramble game with a random word from the dictionary.

        :param session_id: Session identifier for the active chat/game context.
        :param is_team: Whether the game is team-only.
        """
        # check that there isnt already a game running
        if not self.word_list:
            raise ValueError("Scramble dictionary is empty.")
        session_key = session_id or "default"
        if session_key in self.games:
            raise ValueError("A game is already in progress for this session. Please finish the current game before starting a new one.")
        current_word = random.choice(self.word_list)
        scrambled_word = ''.join(random.sample(current_word, len(current_word)))
        self.games[session_key] = {
            "current_word": current_word,
            "scrambled_word": scrambled_word,
            "winner": None,
            "is_team_game": is_team,
        }
        self._sync_reading_input()
        return scrambled_word

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def process(self, playername: str, is_team: bool, chattext: str, session_id: str = "default", t=None) -> str:
        """
        Process a player's guess and check if they unscramble the word.

        :param playername: The name of the player.
        :param is_team: Whether the message is for the team chat.
        :param chattext: The player's guess.
        :return: A response string or None if no action is needed.
        """
        session_key = session_id or "default"
        game = self.games.get(session_key)
        if game and not game["winner"]:
            if game["is_team_game"] and not is_team:
                return None  # Ignore non-team guesses in a team-only game

            # Normalize the user input: lowercase, remove dashes and spaces
            normalized_input = chattext.strip().lower().replace("-", "").replace(" ", "")
            normalized_word = game["current_word"].lower().replace("-", "").replace(" ", "")

            # Check if the input starts with the unscrambled word
            if normalized_input.startswith(normalized_word):
                game["winner"] = playername
                del self.games[session_key]
                self._sync_reading_input()
                # add $100 to the player's balance
                if self.economy:
                    self.economy.add_balance(playername, 100)
                return self._translate(
                    t,
                    "commands.scramble.winner",
                    "{player} unscrambled the word '{word}' correctly and wins $100!",
                    player=playername,
                    word=game["current_word"],
                )
        return None