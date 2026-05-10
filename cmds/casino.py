from util.commands import command_registry
from modules.casino import Casino as CasinoModule

@command_registry.register("flip", aliases=["gamble", "coinflip"])
def flip_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Flip a coin to gamble an amount or the entire balance with "all".

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The amount to gamble (optional, or "all").
    :help flip: Flip a coin to gamble an amount or the entire balance with "all". (alias: gamble, coinflip)
    """
    casino_module: CasinoModule = bot.modules.get_module("casino")
    if casino_module:
        try:
            # Check if the user wants to flip their entire balance
            if chattext.strip().lower() == "all":
                amount = casino_module.economy.get_balance(playername)
                if amount <= 0:
                    bot.add_to_chat_queue(is_team, bot.t("commands.flip.no_balance", player=playername))
                    return
            else:
                # Parse the amount from the chat text
                amount = float(chattext.strip()) if chattext.strip() else 10

            # Perform the flip
            result = casino_module.flip(playername, amount, t=bot.t)
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        except ValueError:
            bot.add_to_chat_queue(is_team, bot.t("commands.flip.invalid_amount", player=playername))
    else:
        bot.add_to_chat_queue(is_team, bot.t("commands.flip.module_not_found", player=playername))


@command_registry.register("blackjack", aliases=["bj"])
def blackjack_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Play one-player blackjack.

    Usage:
            blackjack <bet|all>
      blackjack hit
      blackjack stand
            blackjack double
    """
    casino_module: CasinoModule = bot.modules.get_module("casino")
    if not casino_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.module_not_found", player=playername))
        return

    session_id = bot.get_request_session() if hasattr(bot, "get_request_session") else "default"
    text = chattext.strip().lower()

    if not text:
        bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.usage", player=playername))
        return

    parts = text.split()
    action = parts[0]

    if action in ["hit", "h"]:
        result = casino_module.blackjack_hit(playername, session_id, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        return

    if action in ["stand", "s"]:
        result = casino_module.blackjack_stand(playername, session_id, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        return

    if action in ["double", "dd", "d"]:
        result = casino_module.blackjack_double(playername, session_id, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        return

    # Otherwise treat first token as bet amount.
    if action == "all":
        bet = casino_module.economy.get_balance(playername)
    else:
        try:
            bet = float(action)
        except ValueError:
            bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.usage", player=playername))
            return

    result = casino_module.blackjack_start(playername, session_id, amount=bet, t=bot.t)
    bot.add_to_chat_queue(is_team, f"{playername}: {result}")


@command_registry.register("hit", aliases=["h"])
def blackjack_hit_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """Blackjack shortcut command to hit the current hand."""
    casino_module: CasinoModule = bot.modules.get_module("casino")
    if not casino_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.module_not_found", player=playername))
        return

    session_id = bot.get_request_session() if hasattr(bot, "get_request_session") else "default"
    result = casino_module.blackjack_hit(playername, session_id, t=bot.t)
    bot.add_to_chat_queue(is_team, f"{playername}: {result}")


@command_registry.register("stand", aliases=["s"])
def blackjack_stand_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """Blackjack shortcut command to stand on the current hand."""
    casino_module: CasinoModule = bot.modules.get_module("casino")
    if not casino_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.module_not_found", player=playername))
        return

    session_id = bot.get_request_session() if hasattr(bot, "get_request_session") else "default"
    result = casino_module.blackjack_stand(playername, session_id, t=bot.t)
    bot.add_to_chat_queue(is_team, f"{playername}: {result}")


@command_registry.register("double", aliases=["dd", "d"])
def blackjack_double_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """Blackjack shortcut command to double down on the current hand."""
    casino_module: CasinoModule = bot.modules.get_module("casino")
    if not casino_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.blackjack.module_not_found", player=playername))
        return

    session_id = bot.get_request_session() if hasattr(bot, "get_request_session") else "default"
    result = casino_module.blackjack_double(playername, session_id, t=bot.t)
    bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        