# TOP Clipboard Utilities - Windows

import pyperclip


def copy_to_clipboard(text):
    """Copy text to Windows clipboard."""
    try:
        pyperclip.copy(text)
        return True
    except Exception as e:
        print(f"  Clipboard copy failed: {e}")
        print("  Text was NOT copied to clipboard.")
        return False