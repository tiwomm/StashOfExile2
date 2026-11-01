"""GGG Terms of Service safety check for the code (see TOS.md). Runs on every pull request and in the test suite.

  py tools/check_tos.py      exit 1 (and says where) if anything breaks a rule

What it looks for, in soe2/ and stashofexile2.py:
  - touching the game client: process memory / injection APIs
  - moving or clicking the mouse for the player
  - packet capture / traffic tools
  - input-automation libraries
  - key input (SendInput) anywhere but soe2/overlay.py, the one place that sends the game's own copy key or one chat
    command - and only keyboard input there (INPUT type 1), never mouse (type 0)
  - a screen watcher (a file that captures the screen) that can send keys"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN = {
    "game memory / injection": r"\b(ReadProcessMemory|WriteProcessMemory|OpenProcess|VirtualAllocEx|VirtualProtectEx|"
                               r"CreateRemoteThread|NtReadVirtualMemory|pymem|ReadWriteMemory|frida|SetWindowsHookEx)\b",
    "mouse automation": r"\b(SetCursorPos|mouse_event|SendMouseInput|pyautogui|mouse\.Controller|pydirectinput)\b",
    "packet tools": r"\b(pydivert|scapy|pcap|WinDivert|npcap)\b",
    "input automation libraries": r"^\s*(import|from)\s+(pynput|keyboard|ahk|autohotkey|pyautogui|pydirectinput)\b",
    "old key API": r"\bkeybd_event\b",
}
SENDERS = {os.path.join("soe2", "overlay.py")}               # the only file allowed to send keys
CAPTURE = r"\b(mss|ImageGrab|BitBlt|grim)\b"
SEND = r"\b(SendInput|_send_keys|type_chat|send_copy)\b"


def files():
    out = sorted(glob.glob(os.path.join(ROOT, "soe2", "**", "*.py"), recursive=True))
    return out + [os.path.join(ROOT, "stashofexile2.py")]


def code_lines(text):
    """Lines without comments and docstrings (they may *mention* these words)."""
    text = re.sub(r'"""[\s\S]*?"""', lambda m: "\n" * m.group(0).count("\n"), text)
    return [re.sub(r"#.*$", "", ln) for ln in text.split("\n")]


def check():
    bad = []
    for path in files():
        rel = os.path.relpath(path, ROOT)
        with open(path, encoding="utf-8") as fh:
            lines = code_lines(fh.read())
        joined = "\n".join(lines)
        for what, pat in FORBIDDEN.items():
            for no, ln in enumerate(lines, 1):
                if re.search(pat, ln):
                    bad.append(f"{rel}:{no}: {what}: {ln.strip()[:90]}")
        for no, ln in enumerate(lines, 1):
            if "SendInput" in ln and rel not in SENDERS:
                bad.append(f"{rel}:{no}: SendInput outside soe2/overlay.py")
            if rel in SENDERS and re.search(r"\bINPUT\(\s*0\s*,", ln):
                bad.append(f"{rel}:{no}: mouse input (INPUT type 0)")
        if re.search(CAPTURE, joined) and re.search(SEND, joined) and rel not in SENDERS:
            bad.append(f"{rel}: a screen watcher must never send keys (it captures the screen and can send input)")
    return bad


def main():
    bad = check()
    for b in bad:
        print(b)
    print("OK - GGG ToS check passed (see TOS.md)" if not bad else f"{len(bad)} ToS problem(s) - see TOS.md")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
