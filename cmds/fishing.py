from util.commands import command_registry
from modules.fishing import Fishing as FishingModule

@command_registry.register("cast", aliases=["fish", "gofish"])
def cast_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate casting a fishing rod to catch a fish or item.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        result = fishing_module.fish(playername)
        if result:
            if result.get("type") == "fish":
                # If a fish is caught, display its details
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername} caught a {result['name']} weighing {result['weight']} lbs worth ${result['price']}!"
                )
            elif result.get("type") == "item":
                # If an item is caught, display the item message
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername}: {result['message']}"
                )
            elif result.get("type") == "error":
                # If an error occurs, display the error message
                bot.add_to_chat_queue(
                    is_team,
                    f"{playername}: {result['message']}"
                )
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: You reel in an empty line.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("sack", aliases=["bag"])
def sack_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the contents of the player's fishing sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        sack = fishing_module.get_sack(playername)
        if sack:
            sack_contents = []
            for fish in sack:
                weight = round(fish["weight"], 2)
                price = round(fish["price"], 2)
                fish_name = fish["name"]
                bait = fish.get("bait", 0)
                if bait:
                    fish_name = f"{fish_name} (bait)"
                sack_contents.append(f"{fish_name} ({weight} lbs, ${price})")
            sack_contents_str = ", ".join(sack_contents)
            bot.add_to_chat_queue(is_team, f"{playername}'s sack contains: {sack_contents_str}")
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: Your sack is empty.")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("eat")
def eat_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate eating a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to eat.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip()
        result = fishing_module.eat(playername, fish_name if fish_name else None)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("sell")
def sell_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Sell a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to sell, or 'all' to sell all fish.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip() if chattext else None
        result = fishing_module.sell_fish(playername, fish_name)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")

@command_registry.register("bait")
def bait_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Use bait to increase the chances of catching a fish.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the bait to use.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        if not chattext:
            bait = fishing_module.get_bait(playername)
            if not bait:
                bot.add_to_chat_queue(is_team, f"{playername}: You don't have any bait set.")
                return
        
        # Check if the user wants to clear bait
        if chattext.lower() == "clear":
            result = fishing_module.clear_bait(playername)
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
            return
        
        # If the user provided bait, use it
        bait_name = chattext.strip()
        result = fishing_module.bait(playername, bait_name)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Fishing module not found.")
