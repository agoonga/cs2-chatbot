from modules.casino import Casino
from util.module_registry import module_registry


class FakeEconomy:
    def __init__(self):
        self.balances = {}

    def get_balance(self, user_id):
        return float(self.balances.get(user_id, 0.0))

    def add_balance(self, user_id, amount):
        self.balances[user_id] = round(self.get_balance(user_id) + amount, 2)
        return self.balances[user_id]

    def deduct_balance(self, user_id, amount):
        if self.get_balance(user_id) < amount:
            return {"error": "Insufficient funds."}
        self.balances[user_id] = round(self.get_balance(user_id) - amount, 2)
        return self.balances[user_id]


class FakeStatusEffects:
    def get_effects(self, _user_id):
        return []


def build_casino(start_balance=1000.0, user_id="alice"):
    module_registry.modules.clear()
    economy = FakeEconomy()
    economy.add_balance(user_id, start_balance)
    module_registry.register("economy", economy)
    module_registry.register("status_effects", FakeStatusEffects())
    return Casino(), economy


def test_blackjack_player_blackjack_pays_three_to_two(monkeypatch):
    casino, economy = build_casino()

    # pop order: p1, p2, d1, d2
    deck = [("8", "H"), ("9", "C"), ("K", "D"), ("A", "S")]
    monkeypatch.setattr(casino, "_bj_new_deck", lambda: list(deck))

    result = casino.blackjack_start("alice", "session-1", amount=100)

    assert "Blackjack" in result
    assert "win $150.00" in result
    assert economy.get_balance("alice") == 1150.0


def test_blackjack_push_when_both_have_blackjack(monkeypatch):
    casino, economy = build_casino()

    # pop order: p1, p2, d1, d2
    deck = [("Q", "H"), ("A", "C"), ("K", "D"), ("A", "S")]
    monkeypatch.setattr(casino, "_bj_new_deck", lambda: list(deck))

    result = casino.blackjack_start("alice", "session-1", amount=100)

    assert "Push" in result
    assert economy.get_balance("alice") == 1000.0


def test_blackjack_double_not_allowed_after_hit(monkeypatch):
    casino, economy = build_casino()

    # pop order: p1, p2, d1, d2; next draw for hit -> 4H
    deck = [("4", "H"), ("7", "S"), ("9", "C"), ("6", "D"), ("5", "H")]
    monkeypatch.setattr(casino, "_bj_new_deck", lambda: list(deck))

    start_result = casino.blackjack_start("alice", "session-1", amount=100)
    hit_result = casino.blackjack_hit("alice", "session-1")
    double_result = casino.blackjack_double("alice", "session-1")

    assert "Blackjack started" in start_result
    assert "You draw" in hit_result
    assert "only double down as your first move" in double_result
    assert economy.get_balance("alice") == 900.0


def test_blackjack_stand_wins_when_dealer_busts(monkeypatch):
    casino, economy = build_casino()

    # pop order: p1, p2, d1, d2; dealer draw on stand -> KH
    deck = [("K", "H"), ("6", "S"), ("9", "C"), ("7", "D"), ("10", "H")]
    monkeypatch.setattr(casino, "_bj_new_deck", lambda: list(deck))

    start_result = casino.blackjack_start("alice", "session-1", amount=100)
    stand_result = casino.blackjack_stand("alice", "session-1")

    assert "Blackjack started" in start_result
    assert "You win $100.00" in stand_result
    assert economy.get_balance("alice") == 1100.0
