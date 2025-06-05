import random

from util.module_registry import module_registry
from modules.economy import Economy
from modules.status_effects import StatusEffects

class Casino:
    load_after = ["economy", "status_effects"]  # Load after the economy module
    def __init__(self):
        # Retrieve the Economy module from the module registry
        self.economy: Economy = module_registry.get_module("economy")
        # Retrieve the StatusEffects module from the module registry
        self.status_effects: StatusEffects = module_registry.get_module("status_effects")

    def flip(self, user_id, amount=10):
        """
        Flip a coin to gamble an amount.

        :param user_id: The ID of the user.
        :param amount: The amount to gamble (default is 10).
        :return: A message with the result of the flip.
        """
        if amount <= 0:
            return "No way jose, pick a number greater than 0."

        # Ensure the user has enough balance
        current_balance = self.economy.get_balance(user_id)
        if current_balance < amount:
            return f"Insufficient funds. Your current balance is ${current_balance:.2f}."

        # Perform the coin flip
        # Get cutoff from status effects
        status_effects = self.status_effects.get_effects(user_id)
        cutoff = 0.5
        for effect in status_effects:
            if effect["effect_id"] == "luck":
                cutoff *= effect["mult"]
        outcome = "heads" if random.random() < cutoff else "tails"
        if outcome == "heads":
            # User wins, double the amount
            self.economy.add_balance(user_id, amount)
            return f"You flipped heads and won ${amount:.2f}! Your new balance is ${self.economy.get_balance(user_id):.2f}."
        else:
            # User loses, deduct the amount
            self.economy.deduct_balance(user_id, amount)
            return f"You flipped tails and lost ${amount:.2f}. Your new balance is ${self.economy.get_balance(user_id):.2f}."