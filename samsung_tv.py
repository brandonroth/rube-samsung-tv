"""Samsung TV Wake + Input Switcher

Wakes a Samsung TV via WOL, then switches to a named HDMI input
using the WebSocket remote API.

Setup (Windows):
    1. Install Python 3.9+ from https://www.python.org/downloads/
       - Check "Add python.exe to PATH" during install
    2. Open a terminal (cmd or PowerShell) and run:
       pip install samsungtvws wakeonlan
    3. Place this script, config.json, and tv_token.txt in the same dir
    4. Run:
       python samsung_tv.py pc
       python samsung_tv.py "apple tv"

Configuration:
    Edit config.json to change TV IP, MAC, and the ordered input list.
    The "inputs" array must match the order shown in the TV's source menu.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from samsungtvws import SamsungTVWS
from wakeonlan import send_magic_packet

SCRIPT_DIR = Path(__file__).parent
DEFAULT_CONFIG = SCRIPT_DIR / "config.json"


def load_config(config_path):
    """Load config from JSON file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[-] Config not found: {config_path}")
        sys.exit(1)


def find_input(inputs, target):
    """Find the target input name (case-insensitive) and return its index."""
    target_lower = target.lower()
    for i, name in enumerate(inputs):
        if name.lower() == target_lower:
            return i
    print(f'[-] Unknown input "{target}". Available: {", ".join(inputs)}')
    sys.exit(1)


def parse_args(inputs_list):
    """Parse CLI arguments."""
    p = argparse.ArgumentParser(
        description="Wake Samsung TV and switch input.",
        epilog="Example: python samsung_tv.py pc",
    )
    p.add_argument("input", nargs="?",
                   help=f"Input to switch to: {', '.join(inputs_list)}")
    p.add_argument("--no-wake", action="store_true",
                   help="Skip WOL, just switch input (TV already on)")
    p.add_argument("--wake-only", action="store_true",
                   help="Only send WOL, don't switch input")
    p.add_argument("--list", action="store_true",
                   help="List available inputs and exit")
    return p.parse_args()


def wake_tv(mac):
    """Send WOL magic packets to turn on the TV."""
    print(f"[*] Sending WOL packets to {mac}...")
    for _ in range(3):
        send_magic_packet(mac)
    print("[+] WOL sent.")


def wait_for_tv(ip, timeout=30):
    """Wait for the TV to become reachable on the network."""
    import requests

    print(f"[*] Waiting for TV at {ip} (up to {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        try:
            resp = requests.get(f"http://{ip}:8001/api/v2/", timeout=2)
            if resp.status_code == 200:
                print("[+] TV is online.")
                return True
        except Exception:
            pass
        time.sleep(1)
    print("[-] TV did not respond in time.")
    return False


def switch_input(ip, port, token_file, total_items, target_index):
    """Open the source menu and navigate to the target input by index."""
    print(f"[*] Connecting to {ip}:{port}...")
    tv = SamsungTVWS(
        host=ip,
        port=port,
        token_file=token_file,
        name="PCGameLauncher",
        timeout=10,
        key_press_delay=0,
    )
    tv.open()
    print("[+] Connected.")

    print("[*] Switching input...")
    tv.send_key("KEY_SOURCE")
    time.sleep(0.6)

    # Slam right to guarantee we're at the end
    for _ in range(total_items):
        tv.send_key("KEY_RIGHT")

    time.sleep(0.2)

    # Navigate left from the rightmost item to the target
    left_presses = (total_items - 1) - target_index
    for _ in range(left_presses):
        tv.send_key("KEY_LEFT")

    time.sleep(0.2)

    tv.send_key("KEY_ENTER")
    print("[+] Input switched.")

    time.sleep(0.3)
    tv.close()


def main():
    cfg = load_config(DEFAULT_CONFIG)
    inputs = cfg["inputs"]
    args = parse_args(inputs)

    if args.list:
        for i, name in enumerate(inputs, 1):
            print(f"  {i}. {name}")
        return

    if not args.input and not args.wake_only:
        print(f'[-] Specify an input: {", ".join(inputs)}')
        print("    Or use --wake-only to just turn the TV on.")
        sys.exit(1)

    ip = cfg["tv_ip"]
    mac = cfg["tv_mac"]
    port = cfg["tv_port"]
    boot_delay = cfg["boot_delay"]

    token_file = cfg["token_file"]
    if not Path(token_file).is_absolute():
        token_file = str(SCRIPT_DIR / token_file)

    # Wake
    if not args.no_wake:
        wake_tv(mac)
        if not wait_for_tv(ip):
            print("[-] Could not reach TV. Is it on the same network?")
            sys.exit(1)
        time.sleep(boot_delay)

    if args.wake_only:
        print("[+] Done (wake only).")
        return

    # Switch input
    extra = cfg.get("extra_items_right", 0)
    total_items = len(inputs) + extra
    target_index = find_input(inputs, args.input)
    print(f'[*] Target: {inputs[target_index]}')
    switch_input(ip, port, token_file, total_items, target_index)
    print("[+] Done!")


if __name__ == "__main__":
    main()
