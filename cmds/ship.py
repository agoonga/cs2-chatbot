import random
from util.commands import command_registry

@command_registry.register("ship")
def ship_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Generate a compatibility percentage between the player and the provided name.

    :param bot: The Bot instance.
    :param is_team: If True, send the message to the team chat. If False, send it to the global chat.
    :param playername: The name of the player.
    :param chattext: The name to "ship" with the player.
    """
    if not chattext.strip():
        bot.add_to_chat_queue(is_team, f"{playername}: Please provide a name to ship with!")
        return

    # Concatenate playername and chattext, sort the characters, and use it as the random seed
    combined_name = ''.join(sorted(playername + chattext.strip()))
    random.seed(combined_name)

    # Generate a random compatibility percentage
    compatibility = random.randint(0, 100)

    # Send the result to the chat
    bot.add_to_chat_queue(is_team, f"{playername} and {chattext.strip()} are {compatibility}% compatible!")