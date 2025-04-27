import functools

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

    def register(self, command_name):
        """Decorator to register a command."""
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            wrapper.command_name = command_name
            wrapper.is_bot_command = True
            self.commands[command_name] = func
            return wrapper

        return decorator

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
        if command_name in self.commands:
            return self.commands[command_name](*args, **kwargs)
        else:
            raise ValueError(f"Command '{command_name}' not found.")

    def set_logger(self, logger):
        """Set a custom logger."""
        if self.logger:
            self.logger.removeHandler(self.logger.handlers[0])
        self.logger = logger

    def __len__(self):
        """Return the number of registered commands."""
        return len(self.commands)

# Create a global instance of CommandRegistry
command_registry = CommandRegistry()