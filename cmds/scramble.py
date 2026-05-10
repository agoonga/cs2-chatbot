from util.commands import command_registry
from modules.scramble import Scramble as ScrambleModule

@command_registry.register("scramble")
def scramble_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Start a new scramble game with the given word.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The word to scramble.
    :help scramble: Start a new scramble game.
    """
    scramble_module: ScrambleModule = bot.modules.get_module("scramble")
    if scramble_module:
        session_id = bot.get_request_session() if hasattr(bot, "get_request_session") else "default"
        scrambled_word = scramble_module.start_new_game(session_id, is_team)
        bot.add_to_chat_queue(
            is_team,
            bot.t("commands.scramble.start", word=scrambled_word),
        )
    else:
        bot.add_to_chat_queue(is_team, bot.t("commands.scramble.module_not_found", player=playername))
