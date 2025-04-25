import os
from time import sleep
import win32api
import win32con
import win32gui
import toml
import importlib.util as importlib_util
import inspect

import util.keys as keys


class Bot:
    def __init__(self) -> None:
        self.chat_queue = []
        self.config = self.load_config()
        self.load_chat_key = self.config.get("load_chat_key", "kp_1")  # keypad 1
        self.load_chat_key_win32 = keys.KEYS[self.load_chat_key]
        self.send_chat_key = self.config.get("send_chat_key", "kp_2")  # keypad 2
        self.send_chat_key_win32 = keys.KEYS[self.send_chat_key]
        self.console_log_path = os.path.join(
            os.path.dirname(__file__),
            self.config.get(
                "console_log_path",
                "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/console.log",
            ),
        )
        self.exec_path = os.path.join(
            os.path.dirname(__file__),
            self.config.get(
                "exec_path",
                "C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/csgo/cfg/chat.cfg",
            ),
        )
        self.load_commands()

        # connect to cs2
        cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
        if cs2_hwnd == 0:
            raise Exception("Counter-Strike 2 is not running.")

        win32gui.SetForegroundWindow(cs2_hwnd)

        # open console log file
        if not os.path.exists(self.console_log_path):
            print(f"console log file {self.console_log_path} does not exist.")
            exit(1)

        with open(self.console_log_path, "r", encoding="utf-8") as f:
            # move to the end of the file
            f.seek(0, os.SEEK_END)
            # follow the file for new lines
            while True:
                line = f.readline()
                if not line:
                    sleep(0.1)
                    continue

                # check if the line contains "chat"
                if "@" in line:
                    # get playername
                    print(line)
                    try:
                        # if its not ALL, then its team
                        is_team = line.split("] ")[0].split("  [")[1]
                        print("is_team", is_team)
                        chatline = line.split("] ")[1].split(": ")
                        playername = chatline[0].strip()
                        playername = playername.replace("\u200e", "")
                        if is_team != "ALL":
                            is_team = True
                        else:
                            is_team = False
                        playername = playername.split("\ufe6b")[0]
                        playername = playername.split("[DEAD]")[0]
                        playername = playername.replace("/", "/​")
                        playername = playername.replace("'", "י")
                        playername = playername.strip()
                    except ValueError:
                        print("Line is not chat line", line)
                        continue
                    except IndexError:
                        print("Line is not chat line", line)
                        continue

                    chattext = chatline[1].strip()
                    chattext = chattext.replace(";", ";")
                    chattext = chattext.replace("/", "/​")
                    chattext = chattext.replace("'", "י")
                    chattext = chattext.strip()

                    print(f"chattext: [{chattext}]")
                    possible_cmd = chattext.split(" ")[0]
                    print(f"Command: [{possible_cmd}]")
                    print(f"Chattext: [{chattext}]")
                    print(f"Playername: [{playername}]")
                    
                    if not chattext.startswith("@"):
                        continue
                    print("after continue")

                    possible_cmd = possible_cmd[1:]
                    possible_cmd = possible_cmd.strip()
                    # remove @ from chattext
                    chattext = chattext.replace(f"@{possible_cmd}", "", 1).strip()

                    # check if command exists
                    if possible_cmd in self.commands:
                        print(f"Command found: {chattext}")
                        chattext = chattext.replace(possible_cmd, "", 1).strip()
                        # run command
                        command = self.commands[possible_cmd]
                        command(self, is_team, playername, chattext)

                    self.run_chat_queue()

    def add_to_chat_queue(self, is_team: bool, chattext: str) -> None:
        self.chat_queue.append((is_team, chattext))

    def run_chat_queue(self) -> None:
        # get chat queue
        if self.chat_queue:
            queued = self.chat_queue.pop(0)
            is_team = queued[0]
            chattext = queued[1]

            # write chat to cfg file
            self.write_chat_to_cfg(is_team, chattext)
            sleep(0.5)

            # load chat
            self.load_chat()
            sleep(0.5)

            # send chat
            self.send_chat()
            sleep(0.5)

            self.run_chat_queue()

    def load_commands(self) -> None:
        commands_dir = os.path.join(os.path.dirname(__file__), "cmds")
        self.commands = {}  # Initialize the commands dictionary
        for filename in os.listdir(commands_dir):
            if filename.endswith(".py"):
                module_name = filename[:-3]
                module_path = os.path.join(commands_dir, filename)
                spec = importlib_util.spec_from_file_location(module_name, module_path)
                module = importlib_util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Inspect the module for functions decorated with @bot_command
                for name, obj in inspect.getmembers(module, inspect.isfunction):
                    if getattr(
                        obj, "is_bot_command", False
                    ):  # Check if it's a bot command
                        self.commands[obj.command_name] = obj

        print(f"Loaded commands: {list(self.commands.keys())}")

    # load config
    def load_config(self) -> dict:
        config_path = os.path.join(os.path.dirname(__file__), "config.toml")
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"config file {config_path} does not exist.")
        with open(config_path, "r") as f:
            config = toml.load(f)
        return config

    def load_chat(self) -> None:
        # send load chat key
        win32api.keybd_event(self.load_chat_key_win32, 0, 0, 0)
        win32api.keybd_event(self.load_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)

    def send_chat(self) -> None:
        # send send chat key
        win32api.keybd_event(self.send_chat_key_win32, 0, 0, 0)
        win32api.keybd_event(self.send_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)

    def write_chat_to_cfg(self, is_team: bool, chattext: str) -> None:
        # clear cfg file then write chat to cfg file
        with open(self.exec_path, "w", encoding="utf-8") as f:
            # write chat to cfg file
            if is_team:
                f.write(f'bind "{self.send_chat_key}" say_team "{chattext}"\n')
            else:
                f.write(f'bind "{self.send_chat_key}" say "{chattext}"\n')


if __name__ == "__main__":
    bot = Bot()

    # load commands
    bot.load_commands()
