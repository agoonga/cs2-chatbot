from cmds.casino import dice_command


class FakeEconomy:
    def __init__(self, balance=0.0):
        self._balance = float(balance)

    def get_balance(self, _user_id):
        return self._balance


class FakeCasinoModule:
    def __init__(self, balance=0.0):
        self.economy = FakeEconomy(balance=balance)
        self.calls = []

    def dice_roll(self, playername, amount, guess, t=None):
        self.calls.append((playername, amount, guess))
        return "dice-result"


class FakeModules:
    def __init__(self, casino_module=None):
        self.casino_module = casino_module

    def get_module(self, module_name):
        if module_name == "casino" and self.casino_module is not None:
            return self.casino_module
        return None


class FakeBot:
    def __init__(self, casino_module=None):
        self.modules = FakeModules(casino_module)
        self.messages = []

    def add_to_chat_queue(self, is_team, text):
        self.messages.append((is_team, text))

    def t(self, key, **_kwargs):
        return key


def test_dice_command_handles_missing_module():
    bot = FakeBot(casino_module=None)

    dice_command(bot, True, "alice", "50 high")

    assert bot.messages == [(True, "commands.dice.module_not_found")]


def test_dice_command_rejects_empty_input():
    bot = FakeBot(casino_module=FakeCasinoModule(balance=100.0))

    dice_command(bot, False, "alice", "")

    assert bot.messages == [(False, "commands.dice.usage")]


def test_dice_command_rejects_missing_guess():
    bot = FakeBot(casino_module=FakeCasinoModule(balance=100.0))

    dice_command(bot, False, "alice", "50")

    assert bot.messages == [(False, "commands.dice.usage")]


def test_dice_command_rejects_invalid_bet_text():
    bot = FakeBot(casino_module=FakeCasinoModule(balance=100.0))

    dice_command(bot, False, "alice", "abc high")

    assert bot.messages == [(False, "commands.dice.invalid_bet")]


def test_dice_command_all_with_zero_balance():
    casino_module = FakeCasinoModule(balance=0.0)
    bot = FakeBot(casino_module=casino_module)

    dice_command(bot, True, "alice", "all low")

    assert bot.messages == [(True, "commands.dice.no_balance")]
    assert casino_module.calls == []


def test_dice_command_passes_all_balance_to_module():
    casino_module = FakeCasinoModule(balance=321.5)
    bot = FakeBot(casino_module=casino_module)

    dice_command(bot, True, "alice", "all high")

    assert casino_module.calls == [("alice", 321.5, "high")]
    assert bot.messages == [(True, "alice: dice-result")]


def test_dice_command_passes_numeric_bet_to_module():
    casino_module = FakeCasinoModule(balance=500.0)
    bot = FakeBot(casino_module=casino_module)

    dice_command(bot, False, "alice", "75 4")

    assert casino_module.calls == [("alice", 75.0, "4")]
    assert bot.messages == [(False, "alice: dice-result")]
