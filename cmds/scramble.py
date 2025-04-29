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
    """
    scramble_module: ScrambleModule = bot.modules.get_module("scramble")
    if scramble_module:
        scramble_module.start_new_game(is_team)
        bot.add_to_chat_queue(is_team, f"First person to unscramble the word wins: {scramble_module.scrambled_word}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Scramble module not found.")
