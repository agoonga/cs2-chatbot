import os
from time import sleep
import win32api
import win32con
import win32gui
import toml

import util.keys as keys

# load config
def load_config() -> dict:
    config_path = os.path.join(os.path.dirname(__file__), 'config.toml')
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"config file {config_path} does not exist.")
    with open(config_path, 'r') as f:
        config = toml.load(f)
    return config

def load_chat() -> None:
    # send load chat key
    win32api.keybd_event(load_chat_key_win32, 0, 0, 0)
    win32api.keybd_event(load_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)

def send_chat() -> None:
    # send send chat key
    win32api.keybd_event(send_chat_key_win32, 0, 0, 0)
    win32api.keybd_event(send_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)

def write_chat_to_cfg(is_team: bool, playername: str, chattext: str) -> None:
    # clear cfg file then write chat to cfg file
    with open(exec_path, 'w', encoding='utf-8') as f:
        # write chat to cfg file
        if is_team:
            f.write(f'bind "{send_chat_key}" "say_team {playername} says wubalubadubdub"\n')
        else:
            f.write(f'bind "{send_chat_key}" "say {playername} says wubalubadubdub"\n')

if __name__ == "__main__":
    config = load_config()
    print(config)
    load_chat_key = config.get('load_chat_key', "kp_1") # keypad 1
    load_chat_key_win32 = keys.KEYS[load_chat_key]
    send_chat_key = config.get('send_chat_key', "kp_1") # keypad 2
    send_chat_key_win32 = keys.KEYS[send_chat_key]
    console_log_path = config.get('console_log_path', 'C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/game/csgo/console.log')
    console_log_path = os.path.join(os.path.dirname(__file__), console_log_path)
    exec_path = config.get('exec_path', 'C:/Program Files (x86)/Steam/steamapps/common/Counter-Strike Global Offensive/csgo/cfg/chat.cfg')
    exec_path = os.path.join(os.path.dirname(__file__), exec_path)

    # connect to cs2
    cs2_hwnd = win32gui.FindWindow(None, "Counter-Strike 2")
    if cs2_hwnd == 0:
        raise Exception("Counter-Strike 2 is not running.")

    win32gui.SetForegroundWindow(cs2_hwnd)

    # open console log file
    if not os.path.exists(console_log_path):
        print(f"console log file {console_log_path} does not exist.")
        exit(1)

    chat_queue = []

    with open(console_log_path, 'r', encoding='utf-8') as f:
        # move to the end of the file
        f.seek(0, os.SEEK_END)
        # follow the file for new lines
        while True:
            line = f.readline()
            if not line:
                sleep(0.1)
                continue

            # check if the line contains "chat"
            if "wubalubadubdub" in line:
                # get playername
                print(line)
                try:
                    # if its not ALL, then its team
                    is_team = line.split('] ')[0].split('  [')[1]
                    print("is_team", is_team)
                    chatline = line.split('] ')[1].split(':')
                    playername = chatline[0].strip()
                    playername = playername.replace('\u200e', '')
                    if is_team != "ALL":
                        is_team = True
                    else:
                        is_team = False
                    playername = playername.split('\ufe6b')[0]
                    playername = playername.split('[DEAD]')[0]
                    playername = playername.strip()
                except ValueError:
                    print("Line is not chat line", line)
                    continue
                except IndexError:
                    print("Line is not chat line", line)
                    continue


                chattext = chatline[1].strip()

                # make sure chat starts with wubalubadubdub
                if not chattext.startswith("wubalubadubdub"):
                    continue

                queued = (is_team, playername, chattext)
                chat_queue.append(queued)

            # get chat queue
            if chat_queue:
                queued = chat_queue.pop(0)
                is_team = queued[0]
                playername = queued[1]
                chattext = queued[2]
                # write chat to cfg file
                write_chat_to_cfg(is_team, playername, chattext)

                sleep(.5)
                # load chat
                load_chat()

                sleep(.5)
                # send chat
                send_chat()