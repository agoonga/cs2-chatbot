import random
from util.module_registry import module_registry

class Casino:
    load_after = ["economy"]  # Load after the economy module
    def __init__(self):
        # Retrieve the Economy module from the module registry
        self.economy = module_registry.get_module("economy")

    def flip(self, user_id, amount=10):
        """
        Flip a coin to gamble an amount.

        :param user_id: The ID of the user.
        :param amount: The amount to gamble (default is 10).
        :return: A message with the result of the flip.
        """
        # Ensure the user has enough balance
        current_balance = self.economy.get_balance(user_id)
        if current_balance < amount:
            return f"Insufficient funds. Your current balance is ${current_balance:.2f}."

        # Perform the coin flip
        outcome = random.choice(["heads", "tails"])
        if outcome == "heads":
            # User wins, double the amount
            self.economy.add_balance(user_id, amount)
            return f"You flipped heads and won ${amount:.2f}! Your new balance is ${self.economy.get_balance(user_id):.2f}."
        else:
            # User loses, deduct the amount
            self.economy.deduct_balance(user_id, amount)
            return f"You flipped tails and lost ${amount:.2f}. Your new balance is ${self.economy.get_balance(user_id):.2f}."