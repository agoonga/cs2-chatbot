from util.commands import command_registry
from modules.status_effects import StatusEffects as StatusEffectsModule

@command_registry.register("status", aliases=["effects", "status"])
def status_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Display the player's current status effects.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored for this command).
    :help status: Display your current status effects. (alias: effects)
    """
    status_effects_module: StatusEffectsModule = bot.modules.get_module("status_effects")
    if status_effects_module:
        effects = status_effects_module.get_effects(playername)
        effect_names = [f"{effect['description']} ({effect['duration']}s)" for effect in effects]
        if not effects:
            bot.add_to_chat_queue(is_team, f"{playername}: You have no active status effects.")
            return
        effect_list = ", ".join(effect_names)
        bot.add_to_chat_queue(is_team, f"{playername}'s status effects: {effect_list}")
    else:
        bot.add_to_chat_queue(is_team, f"{playername}: Status Effects module not found.")