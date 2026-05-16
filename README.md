# EyeCursor

## Setup Instructions

### 1. Clone the Repository
```bash
git clone https://github.com/mahmoud-abuqtiesh/Graduation-Project.git
cd Graduation-Project
```

### 2. Create a Virtual Environment
- **macOS/Linux**:
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```
- **Windows (Command Prompt)**:
  ```cmd
  python -m venv venv
  venv\Scripts\activate
  ```
- **Windows (PowerShell)**:
  ```powershell
  python -m venv venv
  venv\Scripts\Activate.ps1
  ```

### 3. Install Python Requirements
```bash
pip install -r requirements.txt
```

### 4. Additional Requirements for Linux
If you are running on Linux, you must install the following system packages:

- `xdotool`
- `xrandr`

Install them using your distribution's package manager. For example, on Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install xdotool x11-xserver-utils
```

## Windows Quickstart

1. Install Python 3.11 or 3.12 (the deps `dlib`, `mediapipe`, `panda3d` lack
   wheels for 3.13+ at the time of writing) from
   <https://www.python.org/downloads/>.
2. Double-click `setup_windows.bat`. It picks the newest 3.11/3.12 it finds,
   creates `venv\`, and installs `requirements.txt`.
   - If `dlib` fails: install Visual Studio Build Tools (Desktop development
     with C++ workload), then re-run.
3. Launch via the batch files (or via desktop shortcuts, see below):
   - `launch.bat` -- main app
   - `launch_criteria.bat` -- criteria app
   - `launch_game.bat` -- game

### Desktop shortcuts (Windows)

Run once after setup:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\create_shortcuts.ps1
```

This drops three shortcuts on your Desktop:

| Shortcut | Launches | Icon |
|---|---|---|
| **EyeCursor App** | `launch.bat` | `assets\eyecursor.ico` |
| **EyeCursor TestLab** | `launch_criteria.bat` | `assets\testlab.ico` |
| **Horsin' Around** | `launch_game.bat` | `assets\horsin_around.ico` |
