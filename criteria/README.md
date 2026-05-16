# EyeCursor TestLab

<p align="center">
  <img src="../assets/icon_256.png" alt="EyeCursor TestLab" width="128">
</p>

<p align="center">
  <b>Fullscreen cursor-control testing for EyeCursor and other input methods.</b>
</p>

TestLab is a standalone PySide6 desktop app for measuring movement, accuracy, tracking, and clicking performance. It is separate from the main EyeCursor tracking system. It does not touch the camera, run any tracking pipeline, or move the cursor. It only watches normal cursor position and mouse clicks during repeatable fullscreen tests.

---

## What's in here

- A session setup screen for participant name, input method label, seed, screen size, and tags/notes.
- Four tasks that run back-to-back: Movement, Accuracy, Tracking, Clicking.
- Per-task scoring plus a weighted final 0-100 score with a rating label (Excellent / Good / Acceptable / Poor / Failed).
- Resume support for paused or stopped sessions.
- Batches, so you can group a set of sessions and export them together.
- JSON and CSV exports per session, per batch, or across everything.

Repeatability comes from the seed plus screen size. Same seed and same screen geometry produce the same target sequence.

---

## Supported platforms

| Platform | Status |
|----------|--------|
| Linux    | Supported |
| Windows  | Supported via Python/PySide6 |
| macOS    | Supported via Python/PySide6 |

macOS and Linux desktop security settings can interfere with fullscreen input and cursor observation. See the platform notes below if something looks off.

---

## Installation

### Prerequisites

- Python 3.10 - 3.12 (3.12 is what we test on)
- Git
- A mouse or whatever cursor-control method you want to evaluate

You don't need a webcam or any EyeCursor model files to run TestLab.

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3-dev python3-venv libgl1-mesa-glx libglib2.0-0 \
    libxcb-xinerama0 libxkbcommon-x11-0 libdbus-1-3 libxcb-cursor0
```

#### Windows

1. Install Python 3.12 from [python.org](https://www.python.org/downloads/) and check **Add to PATH**.
2. Install Git.
3. Use PowerShell or Command Prompt for the commands below.

#### macOS

Install the Apple command line tools:

```bash
xcode-select --install
```

If you don't already have Python 3, grab it from [python.org](https://www.python.org/downloads/macos/) or Homebrew:

```bash
brew install python@3.12
```

---

## Step 1: Clone the repo

```bash
git clone https://github.com/mahmoud-abuqtiesh/Graduation-Project.git
cd Graduation-Project
```

If you got the project as a zip, extract it and `cd` into the extracted folder.

---

## Step 2: Create a virtual environment

Linux / macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows (PowerShell):

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Windows (cmd):

```cmd
python -m venv venv
venv\Scripts\activate.bat
```

---

## Step 3: Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

The full requirements file covers the main EyeCursor tracking app too, so it pulls in more than TestLab strictly needs. TestLab itself only really needs PySide6 and platformdirs. The install takes a few minutes.

---

## Running TestLab

From the project root:

Linux / macOS:

```bash
source venv/bin/activate
python -m criteria.app.main
```

Windows:

```powershell
.\venv\Scripts\Activate.ps1
python -m criteria.app.main
```

There are also launcher scripts under `launchers/`:

```bash
./launchers/launch_criteria.sh    # Linux / macOS
launchers\launch_criteria.bat     # Windows
```

### Desktop shortcut (Linux)

A `.desktop` shortcut can point at `launchers/launch_criteria.sh`. If your desktop blocks the first launch, right-click it and pick **Allow Launching** or **Trust and Launch**.

---

## macOS notes

Quick path on macOS:

```bash
git clone https://github.com/mahmoud-abuqtiesh/Graduation-Project.git
cd Graduation-Project
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
python -m criteria.app.main
```

If macOS pops privacy prompts, allow Terminal or Python from **System Settings > Privacy & Security**. The two that tend to matter:

- Accessibility (affects how Qt observes input).
- Input Monitoring (needed on some setups).

There is no `.app` bundle yet, so running from a terminal is the supported path.

---

## Usage

### 1. Start a session

1. Click **New Session** in the sidebar (or use the **New Session** button on the Dashboard).
2. Enter the participant name or ID.
3. Pick an input method label:
   - Mouse
   - One-Camera Head Pose
   - Two-Camera Head Pose
   - Eye-Gaze Only
   - Custom (then fill in the custom label field)
4. Optionally add tag key/value pairs (e.g. `distance_m` = `0.75`).
5. The seed is auto-generated. You can re-use a previous seed by editing the session in code if you need to.
6. Hit **Start Fullscreen Test**.

### 2. Run through the tasks

Order is fixed:

1. Movement
2. Accuracy
3. Tracking
4. Clicking
5. Final Results

Between tasks there's a transition screen where you can continue, pause, end the session, or jump to current results.

### 3. Controls during a task

| Control | What it does |
|---------|--------------|
| `Esc` | Pause the active task |
| `Q` | Stop the active task and end the session |
| Continue | Start the next task or resume from pause |
| Pause Session | Save and close the fullscreen window |
| End Session | Mark the session as stopped |
| View Results | Jump to the results page |

### 4. Resume a session

1. Open **Resume Session**.
2. Pick an incomplete session from the list.
3. Click **Continue Selected Session**.

Stopped or paused sessions pick back up at the next incomplete task. An incomplete task itself is not resumed mid-trial - it restarts.

### 5. Batches

The Dashboard has **Start Batch** and **End Batch** buttons. While a batch is active, any new session you run is attached to it. You can export a single batch as CSV from the Results page.

---

## Results and exports

The **Results** page shows:

- Final score and rating
- Participant name
- Input method
- Seed
- Screen size
- Per-task scores
- Session status

Export options on that page:

- **Export JSON** - full raw session.
- **Export CSV Summary** - one row, summary plus advanced metrics, suitable for spreadsheets.
- **Export Simple CSV** - just the per-task scores plus your session tags (saved to your Desktop).
- **Export All Sessions CSV** / **Export All Simple CSV** - same thing across every session on disk.
- **Export Batch CSV** - one row per session in the selected batch.

The **Metrics Guide** page in the sidebar explains what each score and metric in the export actually means.

---

## Data storage

Everything is stored under a platformdirs location, organised like this:

```text
<app-data-dir>/
  sessions/
    <session_id>/
      session.json          # the canonical session record
      summary.json          # final scores + advanced metrics
      raw_events.json       # raw per-task data
      movement_trials.csv
      accuracy_trials.csv
      tracking_samples.csv
      clicking_trials.csv
  exports/                  # JSON/CSV produced by the export buttons
  batches/                  # batch metadata + _active.json pointer
  logs/
  theme.json
```

Where that directory lives:

| Platform | Location |
|----------|----------|
| Linux | `~/.local/share/EyeCursor TestLab` |
| Windows | `%LOCALAPPDATA%\EyeCursorTeam\EyeCursor TestLab` |
| macOS | `~/Library/Application Support/EyeCursor TestLab` |

The JSON is the source of truth. The CSVs are written from the same data for convenience.

---

## Tasks and parameters

These are the current defaults baked into the task classes. Trial counts are part of `TaskConfig` (see `criteria/core/models.py`).

### Movement

- Targets vary in size (radii 60, 35, 20 px), placed by the seeded RNG.
- Get the cursor inside the target and hold for **100 ms** to complete the trial.
- A trial times out after **3 seconds**.
- A warning sound plays at 1 second remaining.

### Accuracy

- A single small target per trial (radius 60 px).
- The trial completes when the cursor stays inside the target for **400 ms** (a dwell hold).
- A trial times out after **4 seconds**.
- Pixel error, radius-normalised error, and screen-normalised error are all recorded.

### Tracking

- A target (radius 90 px) moves along a seeded path of 5 smoothed waypoints.
- You hover into it first, hold briefly, then the path starts.
- The cursor is sampled at the task's configured rate while the target moves.
- The task ends after the configured tracking duration.

### Clicking

- The screen shows either "LEFT CLICK" or "RIGHT CLICK".
- Click the requested button. Anything else counts as a wrong-button fail.
- A trial times out after **5 seconds**.
- Logs success, wrong-button, and timeout per trial.

---

## Scoring

Final score is a weighted average of the four per-task scores:

| Task | Weight |
|------|--------|
| Movement | 30% |
| Accuracy | 30% |
| Tracking | 25% |
| Clicking | 15% |

Rating bands:

| Score | Rating |
|-------|--------|
| 90 - 100 | Excellent |
| 75 - 89 | Good |
| 60 - 74 | Acceptable |
| 40 - 59 | Poor |
| 0 - 39 | Failed |

If a task is missing from a session (e.g. the user stopped early), the final score is computed over the tasks that did complete, with weights renormalised.

---

## Known limitations

- TestLab only watches the cursor. It does not start, stop, or talk to the EyeCursor tracking pipeline.
- It does not touch the camera or calibration data.
- Pausing an active task keeps state in memory for the current fullscreen run. Once the fullscreen window closes, an in-progress task is treated as incomplete and will restart from the start of that task on resume.
- Linux cursor sampling depends on X11/Wayland and your desktop's security settings.
- macOS may need privacy permissions for input observation.
- No packaged `.exe` or `.app` yet - run from a terminal.

---

## Troubleshooting

**PySide6 import error.** Activate the venv and reinstall:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

**macOS isn't seeing input.** Open **System Settings > Privacy & Security** and grant Accessibility and Input Monitoring to Terminal or Python.

**Linux desktop shortcut won't launch.** Right-click and choose **Allow Launching**, or run it from a terminal:

```bash
./launchers/launch_criteria.sh
```

**Results page is empty.** Open the data folder shown in **Settings**. Session JSON and CSV files are written after each task finishes, so if a session was aborted before the first task completed, there's nothing to display.
