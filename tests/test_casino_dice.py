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


def build_casino_with_fakes(start_balance=1000.0, user_id="alice"):
    module_registry.modules.clear()

    economy = FakeEconomy()
    economy.add_balance(user_id, start_balance)

    module_registry.register("economy", economy)
    module_registry.register("status_effects", FakeStatusEffects())

    return Casino(), economy


def test_dice_high_win_pays_even_money(monkeypatch):
    casino, economy = build_casino_with_fakes(start_balance=1000.0, user_id="alice")

    monkeypatch.setattr("modules.casino.random.randint", lambda _a, _b: 6)

    result = casino.dice_roll("alice", amount=50, guess="high")

    assert "Rolled 6" in result
    assert "You win $50.00" in result
    assert economy.get_balance("alice") == 1050.0


def test_dice_exact_win_pays_five_to_one(monkeypatch):
    casino, economy = build_casino_with_fakes(start_balance=1000.0, user_id="alice")

    monkeypatch.setattr("modules.casino.random.randint", lambda _a, _b: 3)

    result = casino.dice_roll("alice", amount=50, guess="3")

    assert "Rolled 3" in result
    assert "You win $250.00" in result
    assert economy.get_balance("alice") == 1250.0


def test_dice_exact_loss_deducts_bet(monkeypatch):
    casino, economy = build_casino_with_fakes(start_balance=1000.0, user_id="alice")

    monkeypatch.setattr("modules.casino.random.randint", lambda _a, _b: 5)

    result = casino.dice_roll("alice", amount=50, guess="3")

    assert "Rolled 5" in result
    assert "You lose $50.00" in result
    assert economy.get_balance("alice") == 950.0


def test_dice_rejects_invalid_guess_without_balance_change(monkeypatch):
    casino, economy = build_casino_with_fakes(start_balance=1000.0, user_id="alice")

    monkeypatch.setattr("modules.casino.random.randint", lambda _a, _b: 4)

    result = casino.dice_roll("alice", amount=50, guess="9")

    assert "Invalid guess" in result
    assert economy.get_balance("alice") == 1000.0


def test_dice_rejects_insufficient_funds(monkeypatch):
    casino, economy = build_casino_with_fakes(start_balance=10.0, user_id="alice")

    monkeypatch.setattr("modules.casino.random.randint", lambda _a, _b: 6)

    result = casino.dice_roll("alice", amount=50, guess="high")

    assert "Insufficient funds" in result
    assert economy.get_balance("alice") == 10.0
