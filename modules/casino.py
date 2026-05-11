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
        self.blackjack_games = {}

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

    def _bj_session_key(self, user_id, session_id):
        return (str(user_id), str(session_id or "default"))

    def _bj_new_deck(self):
        ranks = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        suits = ["H", "D", "C", "S"]
        deck = [(rank, suit) for rank in ranks for suit in suits]
        random.shuffle(deck)
        return deck

    def _bj_hand_value(self, hand):
        value = 0
        aces = 0
        for rank, _ in hand:
            if rank in ["J", "Q", "K"]:
                value += 10
            elif rank == "A":
                value += 11
                aces += 1
            else:
                value += int(rank)

        while value > 21 and aces > 0:
            value -= 10
            aces -= 1

        return value

    def _bj_render_hand(self, hand):
        return ", ".join([f"{rank}{suit}" for rank, suit in hand])

    def _bj_draw(self, game):
        if not game["deck"]:
            game["deck"] = self._bj_new_deck()
        return game["deck"].pop()

    def _bj_finish(self, user_id, session_id):
        key = self._bj_session_key(user_id, session_id)
        if key in self.blackjack_games:
            del self.blackjack_games[key]

    def blackjack_start(self, user_id, session_id, amount=10, t=None):
        try:
            bet = float(amount)
        except ValueError:
            return self._translate(t, "commands.blackjack.invalid_amount", "Invalid amount. Please enter a valid number.")

        if bet <= 0:
            return self._translate(t, "commands.blackjack.amount_must_be_positive", "Bet must be greater than 0.")

        key = self._bj_session_key(user_id, session_id)
        if key in self.blackjack_games:
            return self._translate(t, "commands.blackjack.game_already_active", "You already have an active blackjack hand in this session.")

        current_balance = self.economy.get_balance(user_id)
        if current_balance < bet:
            return self._translate(
                t,
                "commands.blackjack.insufficient_funds",
                "Insufficient funds. Your current balance is ${current_balance:.2f}.",
                current_balance=current_balance,
            )

        self.economy.deduct_balance(user_id, bet)

        deck = self._bj_new_deck()
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]
        player_value = self._bj_hand_value(player_hand)
        dealer_value = self._bj_hand_value(dealer_hand)

        player_blackjack = player_value == 21 and len(player_hand) == 2
        dealer_blackjack = dealer_value == 21 and len(dealer_hand) == 2

        if player_blackjack and dealer_blackjack:
            self.economy.add_balance(user_id, bet)
            return self._translate(
                t,
                "commands.blackjack.push_blackjack",
                "Push. Both you and dealer have blackjack. Your bet is returned. Balance: ${new_balance:.2f}.",
                new_balance=self.economy.get_balance(user_id),
            )

        if player_blackjack:
            self.economy.add_balance(user_id, bet * 2.5)
            return self._translate(
                t,
                "commands.blackjack.player_blackjack",
                "Blackjack! You win ${win_amount:.2f}. Balance: ${new_balance:.2f}.",
                win_amount=bet * 1.5,
                new_balance=self.economy.get_balance(user_id),
            )

        if dealer_blackjack:
            return self._translate(
                t,
                "commands.blackjack.dealer_blackjack",
                "Dealer has blackjack. You lose ${bet:.2f}. Balance: ${new_balance:.2f}.",
                bet=bet,
                new_balance=self.economy.get_balance(user_id),
            )

        game = {
            "bet": bet,
            "deck": deck,
            "player_hand": player_hand,
            "dealer_hand": dealer_hand,
        }
        self.blackjack_games[key] = game

        return self._translate(
            t,
            "commands.blackjack.started",
            "Blackjack started. Bet: ${bet:.2f}. Your hand: {player_hand} ({player_value}). Dealer: {dealer_up}, ?",
            bet=bet,
            player_hand=self._bj_render_hand(player_hand),
            player_value=player_value,
            dealer_up=self._bj_render_hand([dealer_hand[0]]),
        )

    def blackjack_hit(self, user_id, session_id, t=None):
        key = self._bj_session_key(user_id, session_id)
        game = self.blackjack_games.get(key)
        if not game:
            return self._translate(t, "commands.blackjack.no_active_game", "You have no active blackjack hand in this session.")

        game["player_hand"].append(self._bj_draw(game))
        player_value = self._bj_hand_value(game["player_hand"])

        if player_value > 21:
            bet = game["bet"]
            self._bj_finish(user_id, session_id)
            return self._translate(
                t,
                "commands.blackjack.bust",
                "Bust. Your hand: {player_hand} ({player_value}). You lose ${bet:.2f}. Balance: ${new_balance:.2f}.",
                player_hand=self._bj_render_hand(game["player_hand"]),
                player_value=player_value,
                bet=bet,
                new_balance=self.economy.get_balance(user_id),
            )

        if player_value == 21:
            return self.blackjack_stand(user_id, session_id, t=t)

        return self._translate(
            t,
            "commands.blackjack.hit",
            "You draw. Your hand: {player_hand} ({player_value}). Dealer: {dealer_up}, ?",
            player_hand=self._bj_render_hand(game["player_hand"]),
            player_value=player_value,
            dealer_up=self._bj_render_hand([game["dealer_hand"][0]]),
        )

    def blackjack_double(self, user_id, session_id, t=None):
        key = self._bj_session_key(user_id, session_id)
        game = self.blackjack_games.get(key)
        if not game:
            return self._translate(t, "commands.blackjack.no_active_game", "You have no active blackjack hand in this session.")

        # Standard blackjack: double is only allowed as the first decision.
        if len(game["player_hand"]) != 2:
            return self._translate(
                t,
                "commands.blackjack.double_not_allowed",
                "You can only double down as your first move.",
            )

        extra_bet = game["bet"]
        current_balance = self.economy.get_balance(user_id)
        if current_balance < extra_bet:
            return self._translate(
                t,
                "commands.blackjack.insufficient_funds",
                "Insufficient funds. Your current balance is ${current_balance:.2f}.",
                current_balance=current_balance,
            )

        self.economy.deduct_balance(user_id, extra_bet)
        game["bet"] += extra_bet

        # Double down draws exactly one card, then the hand stands.
        game["player_hand"].append(self._bj_draw(game))
        player_value = self._bj_hand_value(game["player_hand"])
        if player_value > 21:
            bet = game["bet"]
            self._bj_finish(user_id, session_id)
            return self._translate(
                t,
                "commands.blackjack.bust",
                "Bust. Your hand: {player_hand} ({player_value}). You lose ${bet:.2f}. Balance: ${new_balance:.2f}.",
                player_hand=self._bj_render_hand(game["player_hand"]),
                player_value=player_value,
                bet=bet,
                new_balance=self.economy.get_balance(user_id),
            )

        return self.blackjack_stand(user_id, session_id, t=t)

    def blackjack_stand(self, user_id, session_id, t=None):
        key = self._bj_session_key(user_id, session_id)
        game = self.blackjack_games.get(key)
        if not game:
            return self._translate(t, "commands.blackjack.no_active_game", "You have no active blackjack hand in this session.")

        player_value = self._bj_hand_value(game["player_hand"])
        while self._bj_hand_value(game["dealer_hand"]) < 17:
            game["dealer_hand"].append(self._bj_draw(game))

        dealer_value = self._bj_hand_value(game["dealer_hand"])
        bet = game["bet"]

        if dealer_value > 21 or player_value > dealer_value:
            self.economy.add_balance(user_id, bet * 2)
            result = self._translate(
                t,
                "commands.blackjack.win",
                "You win ${win_amount:.2f}!",
                win_amount=bet,
            )
        elif player_value == dealer_value:
            self.economy.add_balance(user_id, bet)
            result = self._translate(t, "commands.blackjack.push", "Push. Your bet is returned.")
        else:
            result = self._translate(
                t,
                "commands.blackjack.lose",
                "You lose ${bet:.2f}.",
                bet=bet,
            )

        summary = self._translate(
            t,
            "commands.blackjack.stand_result",
            "{result} Your hand: {player_hand} ({player_value}). Dealer hand: {dealer_hand} ({dealer_value}). Balance: ${new_balance:.2f}.",
            result=result,
            player_hand=self._bj_render_hand(game["player_hand"]),
            player_value=player_value,
            dealer_hand=self._bj_render_hand(game["dealer_hand"]),
            dealer_value=dealer_value,
            new_balance=self.economy.get_balance(user_id),
        )

        self._bj_finish(user_id, session_id)
        return summary

    def dice_roll(self, user_id, amount=10, guess="high", t=None):
        """
        Roll a dice (1-6) and compare against a guess.

        :param user_id: The ID of the user.
        :param amount: The amount to bet (default is 10).
        :param guess: The guess: "high" (4-6), "low" (1-3), or a number 1-6.
        :param t: Translation function.
        :return: A message with the result of the dice roll.
        """
        if amount <= 0:
            return self._translate(t, "commands.dice.amount_must_be_positive", "Bet must be greater than 0.")

        # Ensure the user has enough balance
        current_balance = self.economy.get_balance(user_id)
        if current_balance < amount:
            return self._translate(
                t,
                "commands.dice.insufficient_funds",
                "Insufficient funds. Your current balance is ${current_balance:.2f}.",
                current_balance=current_balance,
            )

        # Normalize guess
        guess_lower = guess.strip().lower()

        # Roll the dice (1-6)
        roll = random.randint(1, 6)

        # Determine win/loss
        win = False
        payout_multiplier = 0

        if guess_lower == "high":
            win = roll >= 4
            payout_multiplier = 1.0  # 1:1 payout
        elif guess_lower == "low":
            win = roll <= 3
            payout_multiplier = 1.0  # 1:1 payout
        else:
            # Try to parse as a number for exact guess
            try:
                exact_num = int(guess_lower)
                if exact_num < 1 or exact_num > 6:
                    return self._translate(
                        t,
                        "commands.dice.invalid_guess",
                        "Invalid guess. Use 'high', 'low', or a number 1-6.",
                    )
                win = roll == exact_num
                payout_multiplier = 5.0  # 5:1 payout
            except ValueError:
                return self._translate(
                    t,
                    "commands.dice.invalid_guess",
                    "Invalid guess. Use 'high', 'low', or a number 1-6.",
                )

        # Deduct the bet upfront
        self.economy.deduct_balance(user_id, amount)

        # Calculate payout
        if win:
            payout = amount * (1 + payout_multiplier)
            self.economy.add_balance(user_id, payout)
            result_msg = self._translate(
                t,
                "commands.dice.win",
                "You win ${win_amount:.2f}!",
                win_amount=payout - amount,
            )
        else:
            result_msg = self._translate(
                t,
                "commands.dice.lose",
                "You lose ${bet:.2f}.",
                bet=amount,
            )

        rolled_msg = self._translate(
            t,
            "commands.dice.rolled",
            "Rolled {roll}. Guessed {guess}. {result} Balance: ${new_balance:.2f}.",
            roll=roll,
            guess=guess_lower,
            result=result_msg,
            new_balance=self.economy.get_balance(user_id),
        )

        return rolled_msg

    def slots(self, user_id, amount=10, t=None):
        """
        Spin a 3-reel slot machine.

        Payout rules:
        - 3 matching symbols: 5:1 payout
        - 2 matching symbols: 1:1 payout
        - no match: lose bet
        """
        if amount <= 0:
            return self._translate(t, "commands.slots.amount_must_be_positive", "Bet must be greater than 0.")

        current_balance = self.economy.get_balance(user_id)
        if current_balance < amount:
            return self._translate(
                t,
                "commands.slots.insufficient_funds",
                "Insufficient funds. Your current balance is ${current_balance:.2f}.",
                current_balance=current_balance,
            )

        symbols = ["cherry", "lemon", "bell", "star", "seven"]
        reels = [random.choice(symbols), random.choice(symbols), random.choice(symbols)]

        # Deduct upfront so payout logic is simple and consistent with dice.
        self.economy.deduct_balance(user_id, amount)

        a, b, c = reels
        if a == b == c:
            payout_multiplier = 5.0
            payout = amount * (1 + payout_multiplier)
            self.economy.add_balance(user_id, payout)
            result = self._translate(
                t,
                "commands.slots.win_three",
                "JACKPOT! Three of a kind. You win ${win_amount:.2f}!",
                win_amount=payout - amount,
            )
        elif a == b or b == c or a == c:
            payout_multiplier = 1.0
            payout = amount * (1 + payout_multiplier)
            self.economy.add_balance(user_id, payout)
            result = self._translate(
                t,
                "commands.slots.win_two",
                "Nice! Two matching symbols. You win ${win_amount:.2f}!",
                win_amount=payout - amount,
            )
        else:
            result = self._translate(
                t,
                "commands.slots.lose",
                "No match. You lose ${bet:.2f}.",
                bet=amount,
            )

        reels_text = " | ".join(reels)
        return self._translate(
            t,
            "commands.slots.spun",
            "Slots: [{reels}] {result} Balance: ${new_balance:.2f}.",
            reels=reels_text,
            result=result,
            new_balance=self.economy.get_balance(user_id),
        )