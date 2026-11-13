# Instagram Uploader (Windows / Linux)

Small Tkinter desktop app to upload **Stories, Reels and Posts** to Instagram from a PC.
Built on the unofficial [instagrapi](https://github.com/subzeroid/instagrapi) library.

## Features
- Story (photo/video), Reel, Post; multiple files at once
- Optional cover image and caption
- Password is **never stored**; only the session is saved (private config folder)
- Login with password (+ 2FA code) or with a `sessionid` cookie

## Requirements
- Python 3.10+ with Tkinter
  - Windows: tick "tcl/tk" in the python.org installer (default)
  - Arch: `sudo pacman -S tk`; Debian/Ubuntu: `sudo apt install python3-tk`
- `ffmpeg` in PATH (needed for videos)

## Run
Linux/macOS:
```sh
./run.sh
```
Windows: double-click `run.bat`.

The first run creates a local `.venv` and installs dependencies.

## Login note
Instagram currently rejects password login from instagrapi for many accounts
("Your version of Instagram is out of date"). Workaround: log in on instagram.com,
copy the `sessionid` cookie from your browser dev tools (Application/Storage -> Cookies)
and paste it in the sessionid field. Treat it like a password.

## Disclaimer
This uses Instagram's private API, which violates Instagram's terms and may get an
account restricted or banned. Use at your own risk, preferably on a secondary account.
No affiliation with Instagram/Meta. MIT licensed.
