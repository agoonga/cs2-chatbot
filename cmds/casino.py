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
                    bot.add_to_chat_queue(is_team, f"{playername}: You have no balance to gamble.")
                    return
            else:
                # Parse the amount from the chat text
                amount = float(chattext.strip()) if chattext.strip() else 10

            # Perform the flip
            result = casino_module.flip(playername, amount)
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
        except ValueError:
            bot.add_to_chat_queue(is_team, f"{playername}: Invalid amount. Please enter a valid number.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Casino module not found.")
        