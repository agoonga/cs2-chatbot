import functools
from thefuzz import process, fuzz
from util.localization import get_localization_manager

class CommandRegistry:
    def __init__(self, logger=None):
        if logger is None:
            import logging
            logger = logging.getLogger(__name__)
            logger.setLevel(logging.DEBUG)
            handler = logging.StreamHandler()
            handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
        self.logger = logger
        self.commands = {}
        self._localized_alias_cache = {}

    def register(self, command_name, aliases=None, aliases_pt=None):
        """Decorator to register a command."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            english_aliases = aliases if aliases else []
            portuguese_aliases = aliases_pt if aliases_pt else []
            all_aliases = list(dict.fromkeys(english_aliases + portuguese_aliases))

            wrapper.command_name = command_name
            wrapper.is_bot_command = True
            wrapper.aliases = all_aliases

            self.commands[command_name] = func
            if all_aliases:
                for alias in all_aliases:
                    self.commands[alias] = func
                    self.logger.info(f"Command '{alias}' registered as an alias for '{command_name}'.")
            else:
                self.logger.info(f"Command '{command_name}' registered.")
            return wrapper

        return decorator

    def _get_localized_alias_map(self, language: str, bot=None) -> dict:
        """Build a localized alias->canonical command map from translation files."""
        if not language:
            language = "en_US"

        if language in self._localized_alias_cache:
            return self._localized_alias_cache[language]

        localization = getattr(bot, "_localization", None) or get_localization_manager()
        alias_config = localization.get_value("command_aliases", language=language, default={})

        alias_map = {}
        if isinstance(alias_config, dict):
            for canonical, aliases in alias_config.items():
                if not isinstance(canonical, str) or not isinstance(aliases, list):
                    continue
                canonical_lower = canonical.lower()
                for alias in aliases:
                    if isinstance(alias, str) and alias.strip():
                        alias_map[alias.strip().lower()] = canonical_lower

        self._localized_alias_cache[language] = alias_map
        return alias_map

    def load_commands(self, commands_dir):
        """Load all commands from the specified directory."""
        import os
        import importlib.util as importlib_util
        import inspect

        for filename in os.listdir(commands_dir):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                module_path = os.path.join(commands_dir, filename)
                spec = importlib_util.spec_from_file_location(module_name, module_path)
                module = importlib_util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Inspect the module for functions decorated with @register
                for _, obj in inspect.getmembers(module, inspect.isfunction):
                    self.logger.info(f"Attempting to load command: {obj.__name__}")
                    if getattr(obj, "is_bot_command", False):
                        self.commands[obj.command_name] = obj

    def execute(self, command_name, *args, **kwargs):
        """Execute a registered command."""
        command_lower = command_name.lower()
        if command_lower in self.commands:
            return self.commands[command_lower](*args, **kwargs)

        bot = args[0] if args else None
        if bot and hasattr(bot, "get_request_language"):
            language = bot.get_request_language()
        else:
            language = getattr(bot, "language", "en_US")
        localization = getattr(bot, "_localization", None) or get_localization_manager()
        localized_aliases = self._get_localized_alias_map(language, bot)

        canonical = localized_aliases.get(command_lower)
        if canonical and canonical in self.commands:
            return self.commands[canonical](*args, **kwargs)

        suggestion_space = list(self.commands.keys()) + list(localized_aliases.keys())
        if suggestion_space:
            best_match, score = process.extractOne(command_name, suggestion_space, scorer=fuzz.ratio)
        else:
            best_match, score = None, 0

        self.logger.warning(f"Command '{command_name}' not found. Did you mean '{best_match}'? (Score: {score})")
        # Commands are typically invoked positionally: (bot, is_team, playername, chattext)
        playername = kwargs.get('playername', '')
        if not playername and len(args) >= 3:
            potential_player = args[2]
            if isinstance(potential_player, str):
                playername = potential_player

        if best_match and score >= 55:
            return localization.get_string(
                "errors.command_not_found_with_suggestion",
                language=language,
                player=playername,
                command=command_name,
                suggestion=best_match,
            )

        return localization.get_string(
            "errors.command_not_found",
            language=language,
            player=playername,
            command=command_name,
        )

    def set_logger(self, logger):
        """Set a custom logger."""
        if self.logger:
            self.logger.removeHandler(self.logger.handlers[0])
        self.logger = logger

    def get_all_commands(self):
        """Return a list of all registered commands."""
        return self.commands

    def __len__(self):
        """Return the number of registered commands."""
        return len(self.commands)

# Create a global instance of CommandRegistry
command_registry = CommandRegistry()