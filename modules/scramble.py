import random
import os

class Scramble:
    def __init__(self):
        self.current_word = None
        self.scrambled_word = None
        self.winner = None
        self.is_team_game = False
        self.word_list = self.load_word_list()
        self.reading_input = False  # Indicates whether the module is actively processing input

    def load_word_list(self):
        """
        Load the scramble dictionary from a file.
        """
        file_path = os.path.join(os.path.dirname(__file__), "data", "scramble_dict.txt")
        if not os.path.exists(file_path):
            return []
        with open(file_path, "r") as f:
            return [line.strip() for line in f if line.strip() and not line.startswith("#")]

    def start_new_game(self, is_team: bool):
        """
        Start a new scramble game with a random word from the dictionary.

        :param is_team: Whether the game is team-only.
        """
        if not self.word_list:
            raise ValueError("Scramble dictionary is empty.")
        self.current_word = random.choice(self.word_list)
        self.scrambled_word = ''.join(random.sample(self.current_word, len(self.current_word)))
        self.winner = None
        self.is_team_game = is_team
        self.reading_input = True  # Activate the module for processing input

    def process(self, playername: str, is_team: bool, chattext: str) -> str:
        """
        Process a player's guess and check if they unscramble the word.

        :param playername: The name of the player.
        :param is_team: Whether the message is for the team chat.
        :param chattext: The player's guess.
        :return: A response string or None if no action is needed.
        """
        if self.current_word and not self.winner:
            if self.is_team_game and not is_team:
                return None  # Ignore non-team guesses in a team-only game

            # Normalize the user input: lowercase, remove dashes and spaces
            normalized_input = chattext.strip().lower().replace("-", "").replace(" ", "")
            normalized_word = self.current_word.lower().replace("-", "").replace(" ", "")

            # Check if the input starts with the unscrambled word
            if normalized_input.startswith(normalized_word):
                self.winner = playername
                self.reading_input = False  # Deactivate the module after the game ends
                return f"{playername} unscrambled the word '{self.current_word}' correctly and wins!"
        return None