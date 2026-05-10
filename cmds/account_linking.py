from util.commands import command_registry


@command_registry.register("link")
def link_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    Link your account across platforms or generate a linking code.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: The linking code (if providing one) or empty to generate.
    :help link: Link your account across platforms. Use '!link' to generate a code, then '@link <code>' on another platform.
    """
    account_linking = bot.modules.get_module("account_linking")
    
    if not account_linking:
        bot.add_to_chat_queue(is_team, bot.t("commands.link.module_not_found", player=playername))
        return
    
    code = chattext.strip()
    
    # Determine platform based on bot type (this is a simplification)
    # In practice, you'd need to pass platform info through the server
    platform = getattr(bot, 'platform', 'cs2')  # Default to cs2 for now
    
    if not code:
        # Generate a new code
        generated_code = account_linking.generate_code(platform, playername)
        bot.add_to_chat_queue(
            is_team,
            bot.t(
                "commands.link.code_generated",
                player=playername,
                code=generated_code,
                minutes=account_linking.code_expiry_minutes,
            )
        )
    else:
        # Use a code to link accounts
        result = account_linking.use_code(code, platform, playername, t=bot.t)
        
        if "error" in result:
            bot.add_to_chat_queue(is_team, f"{playername}: {result['error']}")
        else:
            bot.add_to_chat_queue(is_team, f"{playername}: {result['message']}")


@command_registry.register("linked", aliases=["accounts"])
def linked_command(bot, is_team: bool, playername: str, chattext: str) -> None:
    """
    View your linked accounts.

    :param bot: The Bot instance.
    :param is_team: Whether the message is for the team chat.
    :param playername: The name of the player.
    :param chattext: Additional text (ignored).
    :help linked: View all accounts linked to your profile.
    """
    account_linking = bot.modules.get_module("account_linking")
    
    if not account_linking:
        bot.add_to_chat_queue(is_team, bot.t("commands.link.module_not_found", player=playername))
        return
    
    platform = getattr(bot, 'platform', 'cs2')
    linked_accounts = account_linking.get_linked_accounts(platform, playername)
    
    if not linked_accounts:
        bot.add_to_chat_queue(is_team, bot.t("commands.link.no_linked_accounts", player=playername))
        return
    
    # Format the output
    accounts_str = ", ".join([f"{plat}:{ident}" for plat, ident in linked_accounts])
    bot.add_to_chat_queue(is_team, bot.t("commands.link.linked_accounts", player=playername, accounts=accounts_str))
