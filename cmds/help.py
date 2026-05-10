from util.commands import command_registry
from modules.help import Help as HelpModule

@command_registry.register("help", aliases=["commands", "cmds"])
def help_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the list of available commands or help for a specific command.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The command to get help for (optional).
    :help help: Display the list of available commands or help for a specific command. (alias: commands)
    """
    help_module: HelpModule = bot.modules.get_module("help")
    if help_module:
        if chattext.strip():
            command_name = chattext.strip()
            resolved_name = help_module.resolve_command_name(command_name)
            localized_help = None
            if resolved_name:
                localized_key = f"help_texts.{resolved_name}"
                translated = bot.t(localized_key)
                if translated != localized_key:
                    localized_help = f"{resolved_name}: {translated}"

            help_text = localized_help or help_module.get_help(command_name)
            if help_text:
                bot.add_to_chat_queue(is_team, f"{playername}: {help_text}")
            else:
                message = bot.t("commands.help.no_help_available",
                    player=playername, command=command_name)
                bot.add_to_chat_queue(is_team, message)
        else:
            commands_list = help_module.get_all_commands_no_aliases()
            localized_commands = []
            for command in commands_list:
                command_key = f"help_command_names.{command}"
                translated = bot.t(command_key)
                localized_commands.append(translated if translated != command_key else command)
            message = bot.t("commands.help.available_commands",
                player=playername, list=", ".join(localized_commands))
            bot.add_to_chat_queue(is_team, message)
    else:
        message = bot.t("commands.help.module_not_found", player=playername)
        bot.add_to_chat_queue(is_team, message)
