from util.register_cmd import bot_command

@bot_command("say")
def say_command(self, is_team: bool, playername: str, chattext: str) -> None:
    """
    Send a chat message to the game console.

    :param is_team: If True, send the message to the team chat. If False, send it to the global chat.
    :param chattext: The text of the message to send.
    """

    self.add_to_chat_queue(is_team, f'{playername}: "{chattext}"')