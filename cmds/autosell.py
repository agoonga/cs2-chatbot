from util.commands import command_registry
from modules.fishing import Fishing as FishingModule


@command_registry.register("autosell")
def autosell_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Manage autosell fish preferences.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for team chat.
    :param playername: The name of the player.
    :param chattext: Subcommand and fish name.
    :help autosell: Manage fish autosell list. Usage: @autosell [add|remove] <fish>, @autosell clear, @autosell to list.
    """
    fishing_module: FishingModule = bot.modules.get_module("fishing")

    if not fishing_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.autosell.module_not_found", player=playername))
        return

    args = chattext.strip().split()

    if not args:
        fish_names = fishing_module.list_autosell_fish(playername)
        if not fish_names:
            bot.add_to_chat_queue(is_team, bot.t("commands.autosell.list_empty", player=playername))
            return
        bot.add_to_chat_queue(
            is_team,
            bot.t("commands.autosell.list", player=playername, fish_list=', '.join(fish_names)),
        )
        return

    action = args[0].lower()
    fish_name = " ".join(args[1:]).strip() if len(args) > 1 else ""

    if action == "add":
        if not fish_name:
            bot.add_to_chat_queue(is_team, bot.t("commands.autosell.usage_add", player=playername))
            return
        _, message = fishing_module.add_autosell_fish(playername, fish_name)
        bot.add_to_chat_queue(is_team, f"{playername}: {message}")
        return

    if action == "remove":
        if not fish_name:
            bot.add_to_chat_queue(is_team, bot.t("commands.autosell.usage_remove", player=playername))
            return
        _, message = fishing_module.remove_autosell_fish(playername, fish_name)
        bot.add_to_chat_queue(is_team, f"{playername}: {message}")
        return

    if action == "clear":
        _, message = fishing_module.clear_autosell_fish(playername)
        bot.add_to_chat_queue(is_team, f"{playername}: {message}")
        return

    bot.add_to_chat_queue(
        is_team,
        bot.t("commands.autosell.usage_general", player=playername)
    )
