from util.commands import command_registry
import random

@command_registry.register("femboy")
def femboy_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Checks if the user is a femboy.

    :param bot: The Bot instance.
    :param is_team: If True, send the message to the team chat. If False, send it to the global chat.
    :param playername: The name of the player.
    :param chattext: The name to check against (optional).
    """
    femboy = chattext.strip().lower() if chattext.strip() else playername.lower()

    # Using the player's name as the random seed
    random.seed(femboy)
    # Generate a random number between 1 and 100
    femboy_chance = random.randint(1, 100)
    # Determine if the player is a femboy
    is_femboy = femboy_chance > 75

    if femboy == playername.lower():
        bot.add_to_chat_queue(is_team, f'{playername}: "I am a {"femboy" if is_femboy else "not a femboy"} ({femboy_chance}%)"')
    else:
        bot.add_to_chat_queue(is_team, f'{playername}: "{femboy} is a {"femboy" if is_femboy else "not a femboy"} ({femboy_chance}%)"')
        