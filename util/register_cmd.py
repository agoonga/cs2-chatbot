# register command function decorator
import os
import functools
import functools

def bot_command(command_name):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        # Attach the command name and mark it as a bot command
        wrapper.command_name = command_name
        wrapper.is_bot_command = True  # Mark this as a bot command
        return wrapper

    return decorator