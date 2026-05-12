from util.commands import command_registry
from modules.inventory import Inventory as InventoryModule


@command_registry.register("collection", aliases=["mtgcollection", "mtgdex"])
def collection_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Show your discovered MTG card counts by set.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored).
    :help collection: Show discovered MTG cards grouped by set. (aliases: mtgcollection, mtgdex)
    """
    inventory_module: InventoryModule = bot.modules.get_module("inventory")
    if not inventory_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.inventory.module_not_found", player=playername))
        return

    rows = inventory_module.get_mtg_collection_counts_by_set(playername)
    if not rows:
        bot.add_to_chat_queue(is_team, bot.t("commands.collection.empty", player=playername))
        return

    total = inventory_module.get_mtg_collection_total_discovered(playername)
    set_parts = [f"{set_name}: {count}" for set_name, count in rows]
    bot.add_to_chat_queue(
        is_team,
        bot.t(
            "commands.collection.summary",
            player=playername,
            total=total,
            sets=", ".join(set_parts),
        ),
    )
