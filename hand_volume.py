"""Control the Windows master volume with a thumb-and-index pinch."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import cv2
import mediapipe as mp
from comtypes import CLSCTX_ALL
from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume


class HandVolumeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        root.title("Hand Volume Control")
        root.geometry("440x270")
        root.minsize(400, 250)
        root.configure(bg="#10151d")
        root.protocol("WM_DELETE_WINDOW", self.close)

        self.running = False
        self.worker: threading.Thread | None = None
        self.volume = self._volume_interface()
        self.status = tk.StringVar(value="Camera is off")
        self.level = tk.StringVar(value="—")

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", font=("Segoe UI", 10), padding=(14, 9))
        style.configure("TLabel", background="#10151d", foreground="#eef2f8", font=("Segoe UI", 11))

        tk.Label(root, text="HAND VOLUME", bg="#10151d", fg="#8ba7ff",
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=26, pady=(24, 3))
        tk.Label(root, text="Move your fingers. Set your sound.", bg="#10151d", fg="#f3f5fa",
                 font=("Segoe UI", 20, "bold")).pack(anchor="w", padx=26)
        tk.Label(root, text="Pinch thumb and index finger together to lower volume; spread them to raise it.",
                 bg="#10151d", fg="#aab4c3", font=("Segoe UI", 10), wraplength=380,
                 justify="left").pack(anchor="w", padx=26, pady=(9, 17))

        row = tk.Frame(root, bg="#10151d")
        row.pack(fill="x", padx=26)
        self.start_button = ttk.Button(row, text="Start camera", command=self.start)
        self.start_button.pack(side="left")
        tk.Label(row, textvariable=self.level, bg="#10151d", fg="#f3f5fa",
                 font=("Segoe UI", 16, "bold")).pack(side="right")
        tk.Label(root, textvariable=self.status, bg="#10151d", fg="#aab4c3",
                 font=("Segoe UI", 10)).pack(anchor="w", padx=26, pady=(18, 0))
        tk.Label(root, text="Press Q in the camera window to stop", bg="#10151d", fg="#687587",
                 font=("Segoe UI", 9)).pack(anchor="w", padx=26, pady=(5, 0))

    @staticmethod
    def _volume_interface():
        device = AudioUtilities.GetSpeakers()
        interface = device.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        return interface.QueryInterface(IAudioEndpointVolume)

    def start(self) -> None:
        if self.running:
            return
        self.running = True
        self.start_button.configure(text="Camera running", state="disabled")
        self.status.set("Starting webcam…")
        self.worker = threading.Thread(target=self._camera_loop, daemon=True)
        self.worker.start()

    def _camera_loop(self) -> None:
        cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not cap.isOpened():
            self.root.after(0, lambda: self._camera_error("Could not open a webcam. Check camera access and try again."))
            return

        mp_hands = mp.solutions.hands
        detector = mp_hands.Hands(max_num_hands=1, min_detection_confidence=0.65,
                                  min_tracking_confidence=0.6)
        mp_draw = mp.solutions.drawing_utils
        last_update = 0.0
        smooth = None
        try:
            while self.running:
                ok, frame = cap.read()
                if not ok:
                    break
                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = detector.process(rgb)
                percent = None

                if result.multi_hand_landmarks:
                    hand = result.multi_hand_landmarks[0]
                    mp_draw.draw_landmarks(frame, hand, mp_hands.HAND_CONNECTIONS)
                    thumb, index = hand.landmark[4], hand.landmark[8]
                    height, width = frame.shape[:2]
                    a = (int(thumb.x * width), int(thumb.y * height))
                    b = (int(index.x * width), int(index.y * height))
                    distance = ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5
                    cv2.circle(frame, a, 10, (100, 160, 255), -1)
                    cv2.circle(frame, b, 10, (100, 160, 255), -1)
                    cv2.line(frame, a, b, (100, 160, 255), 3)
                    # Map a comfortable pinch range to mute–100%; clamp outside it.
                    target = max(0.0, min(1.0, (distance - 25) / 190))
                    smooth = target if smooth is None else smooth * 0.72 + target * 0.28
                    if time.monotonic() - last_update > 0.07:
                        self.volume.SetMasterVolumeLevelScalar(float(smooth), None)
                        last_update = time.monotonic()
                    percent = round(smooth * 100)
                    cv2.putText(frame, f"Volume  {percent}%", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                0.9, (245, 248, 255), 2, cv2.LINE_AA)
                    self.root.after(0, self._show_volume, percent)
                else:
                    cv2.putText(frame, "Show one hand to the camera", (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                                0.7, (245, 248, 255), 2, cv2.LINE_AA)
                    self.root.after(0, lambda: self.status.set("Looking for a hand…"))

                cv2.imshow("Hand Volume Control  |  Q to stop", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.root.after(0, self.stop)
                    break
        except Exception as exc:
            self.root.after(0, lambda error=str(exc): self._camera_error(f"Volume control stopped: {error}"))
        finally:
            detector.close()
            cap.release()
            cv2.destroyAllWindows()
            self.root.after(0, self._stopped)

    def _show_volume(self, percent: int) -> None:
        self.level.set(f"{percent}%")
        self.status.set("Hand detected · volume follows finger spacing")

    def _camera_error(self, text: str) -> None:
        self.running = False
        self.status.set(text)
        messagebox.showerror("Hand Volume Control", text)
        self._stopped()

    def stop(self) -> None:
        self.running = False
        self.status.set("Stopping camera…")

    def _stopped(self) -> None:
        self.running = False
        self.start_button.configure(text="Start camera", state="normal")
        if self.status.get() == "Stopping camera…":
            self.status.set("Camera is off")

    def close(self) -> None:
        self.running = False
        self.root.after(250, self.root.destroy)


if __name__ == "__main__":
    window = tk.Tk()
    try:
        app = HandVolumeApp(window)
    except Exception as exc:
        messagebox.showerror("Hand Volume Control", f"Could not connect to Windows audio: {exc}")
        window.destroy()
    else:
        window.mainloop()
