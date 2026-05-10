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

    def _translate(self, t, key, default_text, **kwargs):
        if callable(t):
            translated = t(key, **kwargs)
            if translated != key:
                return translated
        return default_text.format(**kwargs)

    def flip(self, user_id, amount=10, t=None):
        """
        Flip a coin to gamble an amount.

        :param user_id: The ID of the user.
        :param amount: The amount to gamble (default is 10).
        :return: A message with the result of the flip.
        """
        if amount <= 0:
            return self._translate(t, "commands.flip.amount_must_be_positive", "No way jose, pick a number greater than 0.")

        # Ensure the user has enough balance
        current_balance = self.economy.get_balance(user_id)
        if current_balance < amount:
            return self._translate(
                t,
                "commands.flip.insufficient_funds",
                "Insufficient funds. Your current balance is ${current_balance:.2f}.",
                current_balance=current_balance,
            )

        # Perform the coin flip
        # Get cutoff from status effects
        status_effects = self.status_effects.get_effects(user_id)
        cutoff = 0.5
        has_luck_effect = False
        for effect in status_effects:
            if effect.get("module_id") == "casino" and effect.get("effect_id", "").startswith("luck"):
                has_luck_effect = True
                cutoff += effect["mult"] - 1

        cutoff = max(0.0, min(1.0, cutoff))
        chance_text = f"{(cutoff * 100):.1f}".rstrip("0").rstrip(".")
        chance_suffix = f" (Luck-adjusted win chance: {chance_text}%.)" if has_luck_effect else ""
        outcome = "heads" if random.random() < cutoff else "tails"
        if outcome == "heads":
            # User wins, double the amount
            self.economy.add_balance(user_id, amount)
            return self._translate(
                t,
                "commands.flip.win_heads",
                "You flipped heads and won ${amount:.2f}! Your new balance is ${new_balance:.2f}.{chance_suffix}",
                amount=amount,
                new_balance=self.economy.get_balance(user_id),
                chance_suffix=chance_suffix,
            )
        else:
            # User loses, deduct the amount
            self.economy.deduct_balance(user_id, amount)
            return self._translate(
                t,
                "commands.flip.lose_tails",
                "You flipped tails and lost ${amount:.2f}. Your new balance is ${new_balance:.2f}.{chance_suffix}",
                amount=amount,
                new_balance=self.economy.get_balance(user_id),
                chance_suffix=chance_suffix,
            )