import pyautogui

def write_chat_to_cfg(exec_path, send_chat_key, is_team, chattext):
    """Write the chat message to the configuration file."""
    with open(exec_path, "w", encoding="utf-8") as f:
        if is_team:
            f.write(f'bind "{send_chat_key}" say_team "{chattext}"\n')
        else:
            f.write(f'bind "{send_chat_key}" say "{chattext}"\n')


def load_chat(load_chat_key):
    """Simulate pressing the load chat key."""
    # win32api.keybd_event(load_chat_key_win32, 0, 0, 0)
    # win32api.keybd_event(load_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)
    pyautogui.press(load_chat_key)


def send_chat(send_chat_key):
    """Simulate pressing the send chat key."""
    # win32api.keybd_event(send_chat_key_win32, 0, 0, 0)
    # win32api.keybd_event(send_chat_key_win32, 0, win32con.KEYEVENTF_KEYUP, 0)
    pyautogui.press(send_chat_key)
