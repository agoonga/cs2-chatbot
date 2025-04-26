from util.commands import command_registry
from util.module_registry import module_registry

@command_registry.register("balance")
def balance_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the player's current balance.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    economy_module = bot.modules.get_module("economy")
    if economy_module:
        balance = economy_module.get_balance(playername)
        bot.add_to_chat_queue(is_team, f"{playername}, your current balance is ${balance:.2f}.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Economy module not found.")

@command_registry.register("top")
def top_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the top players in the economy.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    economy_module = bot.modules.get_module("economy")
    if economy_module:
        top_players = economy_module.get_top_balances()
        if top_players:
            top_list = "\n".join([f"{i+1}. {player['name']} - ${player['balance']:.2f}" for i, player in enumerate(top_players)])
            bot.add_to_chat_queue(is_team, f"Top players:\n{top_list}")
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: No players found.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Economy module not found.")