from util.commands import command_registry


def _format_time_remaining(time_remaining) -> str:
    total_seconds = max(0, int(time_remaining.total_seconds()))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    return f"{hours}h {minutes}m"

@command_registry.register('daily')
@command_registry.register('quest')
def daily_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """View or claim your daily quest. Usage: @daily [claim]"""
    quest_module = bot.modules.get_module('quests')
    if not quest_module:
        bot.add_to_chat_queue(is_team, bot.t("commands.quest.system_not_available"))
        return
    
    args = chattext.split()
    
    if args and args[0].lower() == 'claim':
        success, msg = quest_module.claim_daily_quest(playername)
        bot.add_to_chat_queue(is_team, msg)
        return
    
    # Show current daily quest
    quest = quest_module.get_daily_quest(playername)
    
    if not quest:
        # Check when next quest is available
        time_remaining = quest_module.get_time_until_next_quest(playername)
        if time_remaining:
            bot.add_to_chat_queue(
                is_team,
                bot.t("commands.quest.next_available_in", time_remaining=_format_time_remaining(time_remaining)),
            )
        else:
            bot.add_to_chat_queue(is_team, bot.t("commands.quest.no_daily_available"))
        return
    
    # Check progress
    has_items, missing_item, has_qty, needs_qty = quest_module.check_requirements(
        playername, quest['requirements']
    )
    
    req_text = ", ".join([f"{r['quantity']}x {r['name']}" for r in quest['requirements']])
    
    time_remaining = quest_module.get_time_until_daily_reset(playername)
    reset_text = f" | Resets in {_format_time_remaining(time_remaining)}" if time_remaining else ""

    if not has_items:
        msg = f"[QUEST] {quest['title']}: {req_text} | Need {needs_qty}x {missing_item}, you have {has_qty} | Reward: ${quest['reward_money']:,}{reset_text} | Use @daily claim"
    else:
        msg = f"[QUEST] {quest['title']}: {req_text} | ✓ Ready to claim! | Reward: ${quest['reward_money']:,}{reset_text} | Use @daily claim"
    
    bot.add_to_chat_queue(is_team, msg)

