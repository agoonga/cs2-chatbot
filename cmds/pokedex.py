from util.commands import command_registry
from modules.inventory import Inventory as InventoryModule


@command_registry.register("pokedex", aliases=["dex"])
def pokedex_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Show your discovered Pokemon card counts by region.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored).
    :help pokedex: Show discovered Pokemon cards grouped by region. (alias: dex)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    if not inventory_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.inventory.module_not_found", player=playername))
        return

    rows = inventory_module.get_pokedex_counts_by_region(playername)
    if not rows:
        bot.add_to_chat_queue(is_team, bot.t("commands.pokedex.empty", player=playername))
        return

    total = inventory_module.get_pokedex_total_discovered(playername)
    region_parts = [f"{region}: {count}" for region, count in rows]
    bot.add_to_chat_queue(
        is_team,
        bot.t(
            "commands.pokedex.summary",
            player=playername,
            total=total,
            regions=", ".join(region_parts),
        ),
    )
