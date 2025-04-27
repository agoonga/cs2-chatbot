import os
from util.bot import Bot
from util.ui import UI
import threading
import sys  # Import sys for QApplication
from PyQt6.QtWidgets import QApplication  # Import QApplication
from PyQt6.QtGui import QIcon  # Import QIcon

def start_bot(bot):
    """Start the bot logic in a separate thread."""
    bot.run()  # Assuming you have a `run` method in the Bot class

if __name__ == "__main__":
    # Initialize the QApplication
    app = QApplication(sys.argv)
    icon = QIcon(os.path.join("assets","img","meef.ico"))  # Load the icon
    print(f"Meef icon: {icon}")
    print(f"Meef icon path: {icon.name()}")
    print(f"Meef icon path: {os.path.join('assets','img','meef.ico')}")
    print(f"Meef icon exists: {not icon.isNull()}")
    app.setWindowIcon(icon)  # Set the application icon


    # Start the PyQt6 GUI on the main thread
    ui = UI()
    bot = Bot(ui)  # Pass the UI instance to the Bot

    ui.start(bot)

    # Start the bot logic in a separate thread
    bot_thread = threading.Thread(target=start_bot, args=(bot,))
    bot_thread.daemon = True  # Ensure the thread exits when the main program exits
    bot_thread.start()

    # Start the QApplication event loop
    sys.exit(app.exec())



