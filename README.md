# cs2-chatbot
Python CS2 chat bot by meef (/id/meefaf, meef)

## Architecture
This bot uses a **client-server architecture**:

- **Client** (`./client/adapters/cs2/`): Handles CS2-specific interactions (reading console log, sending chat messages, keyboard hooks)
- **Server** (`./server/`): Handles command processing, module execution, and business logic

Messages are passed from client to server through HTTP POST requests, and responses are returned in the same web request.

For more details, see [ARCHITECTURE.md](ARCHITECTURE.md).

## Installation
To install the bot:
- Install Python 3.10 (I used Python3.10.11)
- Clone the repository, or download as zip and extract
- `cd` to the repo directory
- Run `pip install -r requirements.txt`

## Running the Bot

### Option 1: Run everything together (recommended for most users)
```bash
python cs2chatbot.py
# or
python launcher.py both
```

### Option 2: Run server and client separately
This is useful for debugging or running on separate machines.

**Terminal 1 - Start the server:**
```bash
python launcher.py server
```

**Terminal 2 - Start the client:**
```bash
python launcher.py client
```

## Testing

Unit tests now live under the tests folder and are run with pytest.

Run all unit tests:
```bash
pytest
```

Run only dice-related tests:
```bash
pytest tests/test_casino_dice.py tests/test_casino_command_dice.py
```

Run blackjack and command-localization tests:
```bash
pytest tests/test_casino_blackjack.py tests/test_command_registry_localization.py
```

Manual smoke scripts were grouped under scripts/manual:
- scripts/manual/test_dice_smoke.py
- scripts/manual/test_localization_smoke.py
- scripts/manual/verify_localization_smoke.py
- scripts/manual/test_communication_smoke.py

Legacy root-level entry point still available as a wrapper:
- test_communication.py

## Building Executable
To build a standalone executable:
```bash
pyinstaller cs2chatbot.spec
```
Move the built exe from `dist/cs2chatbot/cs2chatbot.exe` to wherever you'd like.

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
