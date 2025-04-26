# cs2-chatbot
Python CS2 chat bot

## Setup Instructions

### Launch Parameters
To use the bot, make sure to add the following launch parameters to your CS2 game:
- `-condebug`: Enables logging of console output to a file.
- `-conclearlog`: Clears the log file each time the game is launched.

### Configuration
In the `config.toml` file, you must bind the key specified in the configuration to execute the chat command in CS2. For example:
```plaintext
bind "kp_1" "exec chat"
```
