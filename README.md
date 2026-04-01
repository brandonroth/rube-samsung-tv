# Rube Samsung TV

Turns your PC into a Samsung gaming setup.

Some graphics cards don’t do HDMI-CEC, so this exists: a way to control your SmartThings enabled Samsung TV. You can tie it into whatever you want—gaming, automation, or just turning it on without a remote. Overengineered, unnecessary, but it works.

Uses Wake-on-LAN to power on the TV and the Samsung WebSocket API (`samsungtvws`) to simulate remote control keypresses for input switching.

Tested on a QN65S90DAFXZA (2024 S90D OLED, Tizen).

## Setup

### 1. Install uv

uv is a fast Python package manager that handles Python installs and dependencies automatically.

- **macOS/Linux**: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **Windows**: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"`
- **Other methods**: https://docs.astral.sh/uv/getting-started/installation/

### 2. Clone the repo

```bash
git clone https://github.com/brandonroth/rube-samsung-tv
cd rube-samsung-tv
```

### 3. Configure

Copy the example config and edit it:

```bash
cp config.example.json config.json
```

Set `tv_ip` and `tv_mac` in `config.json`. If you know the IP but need the MAC address, query the TV's REST API:

```bash
curl http://<TV_IP>:8001/api/v2/ 
```

This returns the MAC (`wifiMac`), model, firmware, and other device info.

### 4. Run

On first run from a new device, the TV will display an **Allow/Deny** popup. Select **Allow** — a token is saved automatically for future connections.  
```bash
uv run samsung_tv.py pc              # wake TV + switch to PC
uv run samsung_tv.py "apple tv"      # wake TV + switch to Apple TV
uv run samsung_tv.py --no-wake pc    # skip WOL (TV already on)
uv run samsung_tv.py --wake-only     # just turn the TV on
uv run samsung_tv.py --list          # show available inputs
```

**Windows shortcut**: Create a shortcut to `Steam + TV On.bat` on your desktop or taskbar. It wakes the TV, switches to the PC input, and launches Steam — no terminal needed.

## Config Reference

`config.json`:

```json
{
    "tv_ip": "<YOUR_TV_IP>",
    "tv_mac": "<YOUR_TV_MAC>",
    "tv_port": 8002,
    "token_file": "tv_token.txt",
    "boot_delay": 2,
    "inputs": ["TV", "PC", "Apple TV", "HDMI4"], // Update to match inputs on your TV menu
    "extra_items_right": 3
}
```

| Field | Description |
|---|---|
| `tv_ip` | TV's local IP address |
| `tv_mac` | TV's MAC address (for WOL) |
| `tv_port` | WebSocket port. Use `8002` (SSL) for modern Samsung TVs |
| `token_file` | Path to auth token file (relative to script dir) |
| `boot_delay` | Seconds to wait after TV responds before sending keys |
| `inputs` | Ordered list of inputs as they appear in the TV's source menu (left to right) |
| `extra_items_right` | Number of Samsung system items to the right of your inputs in the source menu (e.g. Connection Guide, Remote Access) |

The last two are important as they guide the remote control key logic so it lands on the correct input.

## Updating When Things Change

### TV got a new IP

Update `tv_ip` in `config.json`. Consider giving your TV a static IP or DHCP reservation.

### Samsung firmware added/removed items in the source menu

Open the source menu with your physical remote and count the extra items to the right of your actual HDMI inputs. Update `extra_items_right` in `config.json`.

### Added or rearranged HDMI devices

Update the `inputs` array to match the new left-to-right order in the source menu.

### Auth token stopped working

Delete `tv_token.txt` and run `uv run samsung_tv.py` again — the TV will prompt to re-pair.

### TV won't wake via WOL

- WOL over WiFi is hit-or-miss. Wired ethernet is more reliable.
- Check TV settings: **Settings > General > Network > Expert Settings > Power On with Mobile** must be enabled.
- Some firmware updates disable WOL. Check for a dedicated WOL toggle in network settings.

## Privacy

Samsung requires you to sign into SmartThings during TV setup to enable the network remote API this tool relies on. Once signed in, the TV phones home continuously with telemetry and viewing data.

The workaround:

1. Sign into SmartThings once during setup to unlock the feature
2. Assign the TV a static IP or DHCP reservation on your router
3. Block all outbound internet access for that IP at the router level

The WebSocket API operates entirely on your local network, so blocking external access doesn't affect this tool.

## How It Works

1. Sends WOL magic packets to wake the TV
2. Polls the TV's REST API (`http://<ip>:8001/api/v2/`) until it responds
3. Opens a WebSocket connection on port 8002 (SSL) with a saved auth token
4. Sends `KEY_SOURCE` to open the input menu
5. Slams `KEY_RIGHT` to reach the far-right end of the list
6. Counts `KEY_LEFT` presses to land on the target input
7. Sends `KEY_ENTER` to select

## Files

| File | Tracked | Description |
|---|---|---|
| `samsung_tv.py` | Yes | Main script |
| `config.example.json` | Yes | Config template |
| `pyproject.toml` | Yes | Python dependencies |
| `config.json` | No | Your local config (machine-specific) |
| `tv_token.txt` | No | Auth token from pairing (machine-specific) |
