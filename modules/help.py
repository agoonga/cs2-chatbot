from thefuzz import process

from util.commands import command_registry

class Help:
    def __init__(self):
        self.commands = command_registry.get_all_commands()

    def resolve_command_name(self, command_name: str) -> str:
        """Resolve a fuzzy command input to its canonical command name."""
        match = process.extractOne(command_name, self.commands.keys())
        if not match:
            return None

        matched_name = match[0]
        command = self.commands.get(matched_name)
        if not command:
            return None

        return getattr(command, "command_name", matched_name)
        
    def get_help(self, command_name: str) -> str:
        """
        Get help text for a specific command.
        
        :param command_name: The name of the command to get help for.
        :return: Help text for the command or an error message if not found.
        """
        resolved_name = self.resolve_command_name(command_name)
        if not resolved_name:
            return None

        command = self.commands.get(resolved_name)

        if command:
            # Get the :help line from the docstring
            help_text = command.__doc__
            if help_text:
                # Extract the help text from the docstring
                help_text = help_text.split(":help ")[1].strip()
                return help_text
        return None

    def get_all_commands(self) -> list:
        """
        Get a list of all available commands.
        
        :return: List of command names.
        """
        return list(self.commands)

    def get_all_commands_no_aliases(self) -> list:
        """
        Get a list of all available commands without aliases.
        
        :return: List of command names without aliases.
        """
        hidden_primary_commands = {"hit", "stand", "double"}
        primary_commands = []
        for cmd_name, cmd_func in self.commands.items():
            if getattr(cmd_func, "command_name", None) == cmd_name and cmd_name not in hidden_primary_commands:
                primary_commands.append(cmd_name)
        return primary_commands
