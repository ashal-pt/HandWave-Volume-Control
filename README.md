# Hand Volume Control

A small Windows desktop app that adjusts the system master volume using a webcam. Show one hand, then spread your thumb and index finger to raise volume or pinch them together to lower it. The camera preview shows the tracked hand and current level.

## Run on Windows

Use Python 3.11 (64-bit), then from this folder:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python hand_volume.py
```

Click **Start camera**. Allow camera access if Windows asks. Press **Q** in the preview or close the app to stop.

The app changes Windows' master playback volume. It needs a webcam and permission to use it. The camera feed is processed locally and is not recorded or sent anywhere.
