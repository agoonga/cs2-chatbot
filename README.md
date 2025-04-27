# cs2-chatbot
Python CS2 chat bot by meef (/id/meefaf, meef)

## Installation
To install the bot:
- Install Python 3.10 (I used Python3.10.11)
- Clone the repository, or download as zip and extract
- `cd` to the repo directory
- Run `pip install -r requirements.txt`
- Run `pyinstaller cs2chatbot.spec` 
- Move the built exe from `dist/cs2chatbot/cs2chatbot.exe` to wherever you'd like

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
