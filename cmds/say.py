from util.commands import command_registry

@command_registry.register("say")
def say_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Send a chat message to the game console.

    :param bot: The Bot instance.
    :param is_team: If True, send the message to the team chat. If False, send it to the global chat.
    :param playername: The name of the player.
    :param chattext: The text of the message to send.
    """
    bot.add_to_chat_queue(is_team, f'{playername}: "{chattext}"')
