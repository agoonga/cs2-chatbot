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
            help_text = help_module.get_help(command_name)
            if help_text:
                bot.add_to_chat_queue(is_team, f"{playername}: {help_text}")
            else:
                bot.add_to_chat_queue(is_team, f"{playername}: No help available for '{command_name}'.")
        else:
            commands_list = help_module.get_all_commands_no_aliases()
            bot.add_to_chat_queue(is_team, f"{playername}: Available commands: {', '.join(commands_list)}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Help module not found.")
