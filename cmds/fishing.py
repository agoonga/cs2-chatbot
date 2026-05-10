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
    :help cast: Cast your fishing rod to catch a fish or item. (alias: fish, gofish)
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        result = fishing_module.fish(playername, t=bot.t)
        if result:
            if result.get("type") == "fish":
                # If a fish is caught, display its details
                message = bot.t("commands.fishing.cast_success_fish",
                    player=playername, name=result['name'], 
                    weight=result['weight'], price=result['price'])
                bot.add_to_chat_queue(is_team, message)
            elif result.get("type") == "autosold_fish":
                message = bot.t("commands.fishing.cast_success_autosold",
                    player=playername, name=result['name'], price=result['price'])
                bot.add_to_chat_queue(is_team, message)
            elif result.get("type") == "item":
                # If an item is caught, display the item message
                bot.add_to_chat_queue(is_team, f"{playername}: {result['message']}")
            elif result.get("type") == "error":
                # If an error occurs, display the error message
                bot.add_to_chat_queue(is_team, f"{playername}: {result['message']}")
        else:
            message = bot.t("commands.fishing.empty_line", player=playername)
            bot.add_to_chat_queue(is_team, message)
    else:
        message = bot.t("commands.fishing.module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)

@command_registry.register("sack", aliases=["bag"])
def sack_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the contents of the player's fishing sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    :help sack: Display the contents of your fishing sack. (alias: bag)
    """
    bot.logger.info(f"SACK_COMMAND CALLED for {playername}")
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        sack = fishing_module.get_sack(playername)
        bot.logger.info(f"SACK_COMMAND got sack: {sack}")
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
            message = bot.t("commands.fishing.sack_contents", 
                player=playername, contents=sack_contents_str)
            bot.add_to_chat_queue(is_team, message)
        else:
            message = bot.t("commands.fishing.sack_empty", player=playername)
            bot.add_to_chat_queue(is_team, message)
    else:
        message = bot.t("commands.fishing.sack_module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)

@command_registry.register("eat")
def eat_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Simulate eating a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to eat.
    :help eat: Eat a fish from your sack.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip()
        result = fishing_module.eat(playername, fish_name if fish_name else None, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        message = bot.t("commands.fishing.eat_module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)

@command_registry.register("sell")
def sell_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Sell a fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the fish to sell, or 'all' to sell all fish.
    :help sell: Sell a fish from your sack or 'all' fish.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        fish_name = chattext.strip() if chattext else None
        result = fishing_module.sell_fish(playername, fish_name, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        message = bot.t("commands.fishing.sell_module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)

@command_registry.register("bait")
def bait_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Use bait to increase the chances of catching a fish.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The name of the bait to use.
    :help bait: Use a fish as bait to increase your chances of catching a bigger one. 'last' to use the last fish in your sack, 'clear' to clear bait.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        if not chattext:
            bait = fishing_module.get_bait(playername)
            if not bait:
                message = bot.t("commands.fishing.bait_no_bait_set", player=playername)
                bot.add_to_chat_queue(is_team, message)
                return
        
        # Check if the user wants to clear bait
        if chattext.lower() == "clear":
            result = fishing_module.clear_bait(playername)
            bot.add_to_chat_queue(is_team, f"{playername}: {result}")
            return

        # If the user provided bait, use it
        bait_name = chattext.strip()

        if chattext.lower() == "last":
            # Use the last fish in the sack
            sack = fishing_module.get_sack(playername)
            if not sack:
                message = bot.t("commands.fishing.bait_sack_empty", player=playername)
                bot.add_to_chat_queue(is_team, message)
                return
            last_fish = sack[-1]
            bait_name = last_fish.get("name")
            
        
        result = fishing_module.bait(playername, bait_name, t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        message = bot.t("commands.fishing.bait_module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)

@command_registry.register("sellall")
def sellall_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Sell all fish from the player's sack.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    :help sellall: Sell all fish from your sack at once.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")
    if fishing_module:
        result = fishing_module.sell_fish(playername, "all", t=bot.t)
        bot.add_to_chat_queue(is_team, f"{playername}: {result}")
    else:
        message = bot.t("commands.fishing.sell_module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)
