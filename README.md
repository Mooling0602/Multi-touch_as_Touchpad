# Multi-touch_as_Touchpad

A python script emulates a virtual touchpad device through raw multi-touch input.

## Requirements

- Root permissions (with `sudo`)
- Python package: `libevdev`
> You should better use system package manager to install. For example, in Fedora, install `python3-libevdev` instead.

**NOTE**: Only Linux is supported. macOS, Windows, etc is not supported.

## Tested in

- Moonlight game stream
> I tested with Sunshine server.

## Thanks to

- Gemini: created this script, and make it works.
- ChatGPT: fixed the bugs.
- DeepSeek: added support for drag movement.
- Zed: integration with DeepSeek.
