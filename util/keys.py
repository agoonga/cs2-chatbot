from pyautogui import KEY_NAMES

# map of cs2 bind keys to pyautogui keys
KEYS = {
    "ins": "insert",
    "uparrow": "up",
    "downarrow": "down",
    "leftarrow": "left",
    "rightarrow": "right",
    "kp_0": "num0",
    "kp_1": "num1",
    "kp_2": "num2",
    "kp_3": "num3",
    "kp_4": "num4",
    "kp_5": "num5",
    "kp_6": "num6",
    "kp_7": "num7",
    "kp_8": "num8",
    "kp_9": "num9",
    "kp_del": "decimal",
    "kp_enter": "enter",
    "kp_plus": "add",
    "kp_minus": "subtract",
    "kp_multiply": "multiply",
    "kp_divide": "divide",
    "rshift": "shiftright",
    "rctrl": "ctrlright",
    "ralt": "altright",
    "lshift": "shiftleft",
    "lctrl": "ctrlleft",
    "lalt": "altleft",
}

def get_key(key: str) -> str:
    """Get the pyautogui key name from a cs2 bind key name."""
    # if key is in the KEYS list, return the corresponding value, otherwise return the key itself
    key = key.lower()
    if key in KEYS:
        return KEYS[key]
    return key