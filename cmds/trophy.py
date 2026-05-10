"""
Trophy case commands for managing prized fish.
"""
from util.commands import command_registry


@command_registry.register("trophy")
def trophy_command(server, is_team: bool, playername: str, args: str) -> str:
    """
    Trophy case command - view, add, or remove trophy fish.
    Usage: @trophy [add <fish_name> | remove <number>]
    """
    trophy_module = server.modules.get_module("trophy")
    if not trophy_module:
        return server.t("commands.trophy.module_not_loaded")
    
    args = args.strip()
    
    # If no arguments, show trophy case
    if not args:
        trophies = trophy_module.get_trophies(playername)
        
        if not trophies:
            return server.t("commands.trophy.empty_case", player=playername)
        
        # Format trophy display
        lines = [f"{playername}'s Trophy Case:"]
        total_weight = 0
        total_value = 0
        
        for i, (name, weight, price) in enumerate(trophies, 1):
            lines.append(f"{i}. {name} - {weight:.2f} lbs (${price:.2f})")
            total_weight += weight
            total_value += price
        
        lines.append(f"Total: {len(trophies)}/{trophy_module.MAX_TROPHIES} trophies | {total_weight:.2f} lbs | ${total_value:.2f}")
        
        return " | ".join(lines)
    
    # Parse subcommand
    parts = args.split(maxsplit=1)
    subcommand = parts[0].lower()
    
    if subcommand == "add":
        if len(parts) < 2:
            return server.t("commands.trophy.usage_add", player=playername)
        
        fish_name = parts[1].strip()
        result = trophy_module.add_trophy(playername, fish_name)
        
        if result["success"]:
            return f"{playername}: {result['message']}"
        else:
            return f"{playername}: {result['message']}"
    
    elif subcommand == "remove":
        if len(parts) < 2:
            return server.t("commands.trophy.usage_remove", player=playername)
        
        try:
            trophy_number = int(parts[1].strip())
        except ValueError:
            return server.t("commands.trophy.number_must_be_numeric", player=playername)
        
        result = trophy_module.remove_trophy(playername, trophy_number)
        
        if result["success"]:
            return f"{playername}: {result['message']}"
        else:
            return f"{playername}: {result['message']}"
    
    else:
        return server.t("commands.trophy.unknown_subcommand", player=playername)
