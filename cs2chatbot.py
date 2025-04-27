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
    icon_path = os.path.join("assets", "img", "meef.ico")  # Load the icon
    if hasattr(sys, '_MEIPASS'):
        icon_path = os.path.join(sys._MEIPASS, "assets", "img", "meef.ico")
    icon = QIcon(icon_path)  # Create a QIcon object
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



