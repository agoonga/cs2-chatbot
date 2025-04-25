from util.register_cmd import bot_command
import random

@bot_command("femboy")
def say_command(self, is_team: bool, playername: str, chattext: str) -> None:
    """
    Checks if the user is a femboy.

    :param is_team: If True, send the message to the team chat. If False, send it to the global chat.
    :param chattext: The text of the message to send.
    """

    # using the player's name as the random seed
    random.seed(playername)
    # gen 1-100
    femboy_chance = random.randint(1, 100)
    # if > 75
    is_femboy = femboy_chance > 75

    self.add_to_chat_queue(is_team, f'{playername}: "I am a {"femboy" if is_femboy else "not a femboy"} ({femboy_chance}%)"')