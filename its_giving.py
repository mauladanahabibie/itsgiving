#!/usr/bin/env python3
"""
its_giving.py — meme reactions on top of your face, live in Zoom / Meet.

MediaPipe tracks your face, hands and upper body; when a pose matches, the
matching image or GIF is pasted over your face and the frame goes out through a
virtual camera. See README.md.

  python its_giving.py [--camera 1] [--no-vcam] [--size 640x480] [--no-flip]

Keys:  q quit   d toggle HUD   m switch mode   1-9 0 - = [ p s force-show a pose
"""
import argparse
import os
import platform
import subprocess
import sys
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision
from hand_fx import HandFXRenderer

POSES = ["time_out", "heart", "cover_nose", "crashing_out", "dance", "nose_closed", "flirty",
         "tongue_out", "open_mouth", "disgusted", "talking_to_wall", "suspicious", "spin", "pray", "speed"]
TEST_KEYS = "1234567890-=[ps"

FACE_SCALE = 2.0
HOLD_FRAMES = 10
ARM = {
    "spin": 15, "suspicious": 8, "talking_to_wall": 6, "dance": 6, "crashing_out": 4,
    "open_mouth": 6, "tongue_out": 3, "disgusted": 5, "pray": 3, "speed": 6,
}
T = dict(
    jaw_open=0.5,
    scream_jaw=0.3,
    tongue_jaw=0.15,
    tongue=0.25,
    sneer=0.12,
    disgust=0.6,
    head_turn=0.15,
    squint=0.3,
    gesture=0.035,
    pucker=0.55,
)
INNER_LIPS = [78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191]

MODELS = {
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "hand_landmarker.task": "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task",
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}
HERE = os.path.dirname(os.path.abspath(__file__))


def ensure_models():
    mdir = os.path.join(HERE, "models")
    os.makedirs(mdir, exist_ok=True)
    paths = {}
    for name, url in MODELS.items():
        path = os.path.join(mdir, name)
        if not os.path.exists(path):
            print(f"Downloading {name} ...")
            urllib.request.urlretrieve(url, path)
        paths[name] = path
    return paths


def preflight(model_path):
    """Open a detector in a throwaway subprocess: bad macOS builds abort() uncatchably."""
    code = (
        "import sys\n"
        "from mediapipe.tasks import python as t\n"
        "from mediapipe.tasks.python import vision\n"
        "vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(\n"
        "    base_options=t.BaseOptions(model_asset_path=sys.argv[1]),\n"
        "    running_mode=vision.RunningMode.VIDEO, num_faces=1,\n"
        "    output_face_blendshapes=True)).close()\n"
    )
    proc = subprocess.run([sys.executable, "-c", code, model_path], capture_output=True, text=True)
    if proc.returncode == 0:
        return
    err = (proc.stderr or "") + (proc.stdout or "")
    print(f"\nMediaPipe cannot start a detector here (python {platform.python_version()}, "
          f"mediapipe {getattr(mp, '__version__', '?')}, exit {proc.returncode}).\n")
    if "Service is unavailable" in err or "MetalHelper" in err or proc.returncode == -6:
        print("Cause: mediapipe 0.10.30+ ships macOS wheels that abort on startup.\n"
              "Fix (Python 3.11 or 3.12) — install the pinned set:\n"
              "  pip install -r requirements.txt\n"
              "If you already installed something newer by hand, force it back:\n"
              '  pip install "mediapipe==0.10.21" "numpy<2" "opencv-python<5" "opencv-contrib-python<5"\n')
    else:
        print(err[-1500:])
    sys.exit(1)


def build_detectors(model_paths):
    face = vision.FaceLandmarker.create_from_options(vision.FaceLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["face_landmarker.task"]),
        running_mode=vision.RunningMode.VIDEO, num_faces=1, output_face_blendshapes=True))
    hand = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["hand_landmarker.task"]),
        running_mode=vision.RunningMode.VIDEO, num_hands=2))
    pose = vision.PoseLandmarker.create_from_options(vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=model_paths["pose_landmarker_lite.task"]),
        running_mode=vision.RunningMode.VIDEO, num_poses=1))
    return face, hand, pose


class WindowController:
    """Track window minimize and visibility state, auto-hiding window when minimized to bypass Windows OS 10 FPS camera throttling."""

    def __init__(self, window_name, initial_hide=False):
        self.name = window_name
        self.hwnd = None
        self.hidden = initial_hide
        self.created = False

    def update(self):
        if sys.platform == "win32":
            try:
                import ctypes
                if not self.hwnd:
                    self.hwnd = ctypes.windll.user32.FindWindowW(None, self.name)
                if self.hwnd and not self.hidden:
                    if ctypes.windll.user32.IsIconic(self.hwnd):
                        ctypes.windll.user32.ShowWindow(self.hwnd, 0)  # SW_HIDE
                        self.hidden = True
                        print("\n[Notice] Preview window hidden to maintain full 30 FPS virtual camera stream. Press 'h' to restore.")
            except Exception:
                pass

    def show(self):
        self.hidden = False
        if sys.platform == "win32" and self.hwnd:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            except Exception:
                pass

    def hide(self):
        self.hidden = True
        if sys.platform == "win32" and self.hwnd:
            try:
                import ctypes
                ctypes.windll.user32.ShowWindow(self.hwnd, 0)  # SW_HIDE
            except Exception:
                pass

    def toggle(self):
        if self.hidden:
            self.show()
        else:
            self.hide()


class HotkeyManager:
    """Track keyboard input from OpenCV window, terminal console (msvcrt), and global hotkeys."""

    def __init__(self):
        self.prev_m = False
        self.prev_h = False

    def poll(self):
        # 1. OpenCV window key (if window is active/focused)
        k = cv2.pollKey() & 0xFF if hasattr(cv2, "pollKey") else cv2.waitKey(1) & 0xFF
        if k != 255 and k != 0:
            return chr(k).lower()

        # 2. Terminal console key (when terminal is focused, e.g. in --hide mode)
        if sys.platform == "win32":
            try:
                import msvcrt
                if msvcrt.kbhit():
                    ch = msvcrt.getch()
                    if ch in (b"\x00", b"\xe0"):
                        msvcrt.getch()
                        return None
                    return ch.decode("ascii", errors="ignore").lower()
            except Exception:
                pass

        # 3. Global hotkeys on Windows (Ctrl+Alt+M for mode, Ctrl+Alt+H for hide/show)
        if sys.platform == "win32":
            try:
                import ctypes
                u32 = ctypes.windll.user32
                ctrl = bool(u32.GetAsyncKeyState(0x11) & 0x8000)
                alt = bool(u32.GetAsyncKeyState(0x12) & 0x8000)
                if ctrl and alt:
                    m_down = bool(u32.GetAsyncKeyState(ord("M")) & 0x8000)
                    if m_down and not self.prev_m:
                        self.prev_m = True
                        return "m"
                    elif not m_down:
                        self.prev_m = False

                    h_down = bool(u32.GetAsyncKeyState(ord("H")) & 0x8000)
                    if h_down and not self.prev_h:
                        self.prev_h = True
                        return "h"
                    elif not h_down:
                        self.prev_h = False
                else:
                    self.prev_m = False
                    self.prev_h = False
            except Exception:
                pass

        return None


class Asset:
    """One reaction: a list of BGRA frames plus per-frame durations (ms) for GIFs."""

    def __init__(self, frames, durations):
        self.frames = frames
        self.durations = durations
        self.cum = np.cumsum(durations)
        self.total = int(self.cum[-1])
        h, w = frames[0].shape[:2]
        self.aspect = w / h
        self._cache = {}

    def frame_at(self, ms):
        if len(self.frames) == 1:
            return 0
        return int(np.searchsorted(self.cum, ms % self.total, side="right"))

    def scaled(self, idx, height):
        key = (idx, height)
        if key not in self._cache:
            if len(self._cache) > 64:
                self._cache.clear()
            w = max(1, int(round(height * self.aspect)))
            self._cache[key] = cv2.resize(self.frames[idx], (w, height), interpolation=cv2.INTER_AREA)
        return self._cache[key]


def to_bgra(img):
    if img.ndim == 2:
        return cv2.cvtColor(img, cv2.COLOR_GRAY2BGRA)
    if img.shape[2] == 3:
        return cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img


def placeholder(label):
    img = np.zeros((300, 300, 4), np.uint8)
    cv2.circle(img, (150, 150), 140, (0, 0, 255, 220), -1)
    cv2.putText(img, label, (12, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255, 255), 2)
    return Asset([img], [100])


def find_asset_file(pose):
    adir = os.path.join(HERE, "assets")
    if not os.path.isdir(adir):
        return None
    exts = (".gif", ".png", ".jpg", ".jpeg")
    for fn in sorted(os.listdir(adir)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() in exts and (stem == pose or stem.endswith("_" + pose)):
            return os.path.join(adir, fn)
    return None


def load_asset(pose):
    path = find_asset_file(pose)
    if path is None:
        print(f"  {pose:16s} missing -> placeholder")
        return placeholder(pose)
    frames, durations = [], []
    if path.lower().endswith(".gif"):
        from PIL import Image, ImageSequence
        with Image.open(path) as im:
            for f in ImageSequence.Iterator(im):
                frames.append(cv2.cvtColor(np.array(f.convert("RGBA")), cv2.COLOR_RGBA2BGRA))
                durations.append(max(20, int(f.info.get("duration", 100))))
    else:
        img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if img is not None:
            frames, durations = [to_bgra(img)], [100]
    if not frames:
        print(f"  {pose:16s} could not read {os.path.basename(path)} -> placeholder")
        return placeholder(pose)
    print(f"  {pose:16s} {os.path.basename(path)}  ({len(frames)} frame{'s' if len(frames) > 1 else ''})")
    return Asset(frames, durations)


def overlay(frame, sprite, x, y):
    """Alpha-composite BGRA sprite onto BGR frame at top-left (x, y), clipped to the frame."""
    H, W = frame.shape[:2]
    h, w = sprite.shape[:2]
    x0, y0, x1, y1 = max(x, 0), max(y, 0), min(x + w, W), min(y + h, H)
    if x0 >= x1 or y0 >= y1:
        return frame
    s = sprite[y0 - y:y1 - y, x0 - x:x1 - x]
    a = s[:, :, 3:4].astype(np.float32) / 255.0
    roi = frame[y0:y1, x0:x1].astype(np.float32)
    frame[y0:y1, x0:x1] = (a * s[:, :, :3] + (1 - a) * roi).astype(np.uint8)
    return frame


def dist(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


class Face:
    def __init__(self, lms, blendshapes, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.pts = p
        x0, y0 = p.min(0)
        x1, y1 = p.max(0)
        self.box = (int(x0), int(y0), int(x1), int(y1))
        self.w, self.h = float(x1 - x0), float(y1 - y0)
        self.center = ((x0 + x1) / 2, (y0 + y1) / 2)
        self.nose, self.chin, self.top = p[1], p[152], p[10]
        self.mouth = (p[13] + p[14]) / 2
        self.eye_y = float((p[33][1] + p[263][1]) / 2)
        cl, cr = p[234], p[454]
        self.turn = abs((self.nose[0] - cl[0]) / max(cr[0] - cl[0], 1e-3) - 0.5)
        self.bs = {c.category_name: c.score for c in (blendshapes or [])}

    def b(self, name):
        return self.bs.get(name, 0.0)


class Hand:
    def __init__(self, lms, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.pts = p
        self.wrist = p[0]
        self.palm = p[[0, 5, 9, 13, 17]].mean(0)
        self.thumb, self.index, self.middle = p[4], p[8], p[12]
        self.ring, self.pinky = p[16], p[20]
        d = p[9] - p[0]
        self.horizontal = abs(d[0]) > 1.5 * abs(d[1])
        self.vertical = abs(d[1]) > 1.5 * abs(d[0])
        self.thumb_ext = (dist(p[1], p[4]) > 1.20 * dist(p[1], p[2])) and (dist(p[0], p[4]) > 1.10 * dist(p[0], p[2]))
        self.index_ext = (dist(p[5], p[8]) > 1.25 * dist(p[5], p[6])) and (dist(p[0], p[8]) > 1.05 * dist(p[0], p[6]))
        self.middle_ext = (dist(p[9], p[12]) > 1.25 * dist(p[9], p[10])) and (dist(p[0], p[12]) > 1.05 * dist(p[0], p[10]))
        self.ring_ext = (dist(p[13], p[16]) > 1.25 * dist(p[13], p[14])) and (dist(p[0], p[16]) > 1.05 * dist(p[0], p[14]))
        self.pinky_ext = (dist(p[17], p[20]) > 1.25 * dist(p[17], p[18])) and (dist(p[0], p[20]) > 1.05 * dist(p[0], p[18]))
        ext_count = sum([self.index_ext, self.middle_ext, self.ring_ext, self.pinky_ext])
        self.open = ext_count >= 3

        index_mid_len = (dist(p[5], p[8]) + dist(p[9], p[12])) / 2.0
        ring_pinky_len = (dist(p[13], p[16]) + dist(p[17], p[20])) / 2.0

        self.is_peace = bool(self.index_ext and self.middle_ext and 
                             (index_mid_len > 1.35 * ring_pinky_len) and
                             not (self.ring_ext and self.pinky_ext))
        self.is_thumbs_up = bool(self.thumb_ext and ext_count == 0 and p[4][1] < p[2][1] and p[4][1] < p[5][1])
        self.is_fist = bool(ext_count == 0 and not self.is_thumbs_up)
        self.is_pointing = bool(self.index_ext and not self.thumb_ext and ext_count == 1)
        self.is_gun = bool(self.index_ext and self.thumb_ext and not self.middle_ext and not self.ring_ext and not self.pinky_ext)
        horns = bool(self.index_ext and self.pinky_ext and not self.middle_ext and not self.ring_ext)
        self.is_spiderman = bool(horns and self.thumb_ext)
        self.is_rock_on = bool(horns and not self.thumb_ext)
        self.is_six = bool(self.thumb_ext and self.pinky_ext and not self.index_ext and not self.middle_ext and not self.ring_ext)
        self.is_repulsor = bool(self.open and self.ring_ext and self.pinky_ext and 
                                not self.is_spiderman and not self.is_rock_on and not self.is_peace and not self.is_six)


class Body:
    """Upper-body pose: shoulders 11/12, elbows 13/14, wrists 15/16."""

    def __init__(self, lms, W, H):
        p = np.array([[l.x * W, l.y * H] for l in lms], np.float32)
        self.shoulders, self.elbows, self.wrists = p[[11, 12]], p[[13, 14]], p[[15, 16]]
        vis = [getattr(lms[i], "visibility", 1.0) for i in (11, 12, 13, 14)]
        self.seen = min(vis) > 0.5
        shoulder_y = float(self.shoulders[:, 1].mean())
        self.elbows_up = self.seen and bool((self.elbows[:, 1] < shoulder_y).all())
        wvis = [getattr(lms[i], "visibility", 1.0) for i in (15, 16)]
        self.wrists_seen = min(wvis) > 0.35


def tongue_score(frame, face, hands):
    """Fraction of the mouth opening that reads pink: saturated and lit, unlike teeth or throat."""
    if face.b("jawOpen") < T["tongue_jaw"]:
        return 0.0
    if any(dist(h.palm, face.mouth) < 0.7 * face.w for h in hands):
        return 0.0
    poly = face.pts[INNER_LIPS].astype(np.int32)
    x0, y0 = poly.min(0)
    x1, y1 = poly.max(0)
    if x1 - x0 < 8 or y1 - y0 < 8:
        return 0.0
    x0, y0 = max(x0, 0), max(y0, 0)
    roi = frame[y0:y1 + 1, x0:x1 + 1]
    if roi.size == 0:
        return 0.0
    mask = np.zeros(roi.shape[:2], np.uint8)
    cv2.fillPoly(mask, [poly - [x0, y0]], 255)
    k = max(2, int(0.10 * (y1 - y0)))
    mask = cv2.erode(mask, np.ones((k, k), np.uint8))
    n = int(np.count_nonzero(mask))
    if n < 20:
        return 0.0
    h, s, v = cv2.split(cv2.cvtColor(roi, cv2.COLOR_BGR2HSV))
    pink = ((h < 15) | (h > 155)) & (s > 50) & (v > 80)
    return float(np.count_nonzero(pink & (mask > 0)) / n)


class Motion:
    """Smoothed hand speed across frames, in face-widths per frame."""

    def __init__(self):
        self.prev, self.energy, self.fw = [], 0.0, 200.0

    def update(self, hands, face):
        if face is not None:
            self.fw = max(face.w, 1.0)
        cur = [h.palm for h in hands]
        speed = 0.0
        if cur and self.prev:
            moved = [min(dist(c, p) for p in self.prev) for c in cur]
            moved = [m for m in moved if m < self.fw]
            if moved:
                speed = max(moved) / self.fw
        self.energy = 0.8 * self.energy + 0.2 * speed
        self.prev = cur
        return self.energy


def decide(face, hands, body, tongue, gesture):
    """Return (pose or None, debug dict)."""
    d = {"hands": len(hands)}
    if face is None:
        gone = not hands and (body is None or not body.seen)
        return ("spin" if gone else None), d

    fw = face.w
    near = lambda a, b, k: dist(a, b) < k * fw
    jaw = face.b("jawOpen")
    elbows_up = bool(body and body.elbows_up)
    pair = lambda n: (face.b(n + "Left") + face.b(n + "Right")) / 2
    sneer, brow_down, frown, lip_up = pair("noseSneer"), pair("browDown"), pair("mouthFrown"), pair("mouthUpperUp")
    disgust = 2 * sneer + brow_down + frown + lip_up
    squint = max((face.b("eyeSquintLeft") + face.b("eyeSquintRight")) / 2,
                 (face.b("eyeBlinkLeft") + face.b("eyeBlinkRight")) / 2)
    pucker = face.b("mouthPucker")
    d.update(jaw=jaw, tongue=tongue, disgust=disgust, sneer=sneer, brow=brow_down, frown=frown, lip=lip_up,
             turn=face.turn, squint=squint, gesture=gesture, elbows_up=elbows_up, pucker=pucker)

    wrists_together = bool(body and getattr(body, "wrists_seen", body.seen)
                           and dist(body.wrists[0], body.wrists[1]) < 0.95 * fw
                           and body.wrists[0][1] > face.chin[1] - 0.3 * fw
                           and body.wrists[0][1] < face.chin[1] + 2.2 * fw
                           and abs((body.wrists[0][0] + body.wrists[1][0]) / 2 - face.nose[0]) < 1.2 * fw)

    if len(hands) >= 2:
        a, b = hands[0], hands[1]
        for top, under in ((a, b), (b, a)):
            if top.horizontal and under.vertical and top.palm[1] < under.palm[1] \
                    and near(under.middle, top.palm, 0.6):
                return "time_out", d
        if near(a.index, b.index, 0.3) and near(a.thumb, b.thumb, 0.3) \
                and (a.index[1] + b.index[1]) < (a.thumb[1] + b.thumb[1]):
            return "heart", d
        palms_close = near(a.palm, b.palm, 0.95)
        fingers_up = a.middle[1] < a.palm[1] + 0.35 * fw and b.middle[1] < b.palm[1] + 0.35 * fw
        in_chest = (a.palm[1] > face.eye_y and b.palm[1] > face.eye_y
                    and abs((a.palm[0] + b.palm[0]) / 2 - face.nose[0]) < 1.3 * fw)
        if (palms_close or wrists_together) and fingers_up and in_chest:
            return "pray", d
        if near(a.palm, face.mouth, 0.6) and near(b.palm, face.mouth, 0.6):
            return "cover_nose", d
        on_head = lambda h: (h.palm[1] < face.eye_y and abs(h.palm[0] - face.nose[0]) < 1.1 * fw
                             and h.palm[1] > face.top[1] - 0.8 * face.h)
        if on_head(a) and on_head(b) and jaw > T["scream_jaw"]:
            return "crashing_out", d

    if wrists_together:
        if not hands:
            return "pray", d
        if len(hands) == 1:
            h = hands[0]
            if h.palm[1] > face.eye_y and h.middle[1] < h.palm[1] + 0.35 * fw and abs(h.palm[0] - face.nose[0]) < 1.3 * fw:
                return "pray", d

    near_head = lambda h: abs(h.palm[0] - face.nose[0]) < 1.3 * fw and h.palm[1] < face.eye_y + 0.3 * face.h
    if elbows_up and all(near_head(h) for h in hands):
        return ("crashing_out" if jaw > T["scream_jaw"] else "dance"), d

    for h in hands:
        if near(h.thumb, face.nose, 0.35) and near(h.index, face.nose, 0.35) and near(h.thumb, h.index, 0.3):
            return "nose_closed", d
        if near(h.index, face.mouth, 0.22) and not near(h.palm, face.mouth, 0.3):
            return "flirty", d

    if tongue > T["tongue"]:
        return "tongue_out", d
    if jaw > T["jaw_open"]:
        return "open_mouth", d
    if pucker > T["pucker"] and squint >= 0.22 and jaw < 0.22:
        return "speed", d
    if sneer > T["sneer"] or disgust > T["disgust"]:
        return "disgusted", d
    if hands and gesture > T["gesture"]:
        return "talking_to_wall", d
    if face.turn > T["head_turn"] and squint > T["squint"]:
        return "suspicious", d
    return None, d


def draw_hud(img, mode, hand_gesture, shown, raw, d, face, hands, body):
    if face:
        x0, y0, x1, y1 = face.box
        cv2.rectangle(img, (x0, y0), (x1, y1), (0, 255, 0), 1)
    for h in hands:
        cv2.circle(img, (int(h.palm[0]), int(h.palm[1])), 6, (0, 200, 255), -1)
    if body and body.seen:
        for pt in np.vstack([body.shoulders, body.elbows]):
            cv2.circle(img, (int(pt[0]), int(pt[1])), 6, (255, 120, 0), -1)
    if mode == "hand":
        lines = [
            ("MODE: [HAND FX]  (press 'm' to switch to MEME)", (0, 255, 255)),
            (f"Hands: {len(hands)}   Active FX: {hand_gesture or 'None'}", (0, 255, 0)),
            ("Gestures: 🤟 Spiderman  👐 Kamehameha  🙌 Genkidama  ⚖️ 6 7 Motion", (200, 200, 255)),
            ("          ✊ Claws      ✋ Repulsor    🤘 Rock On    👉 Gun", (200, 200, 255)),
            ("          ☝️ Eldritch   ✌️ Peace       👍 +1000 Aura 🤙 Shaka 6", (200, 200, 255)),
            ("keys: q quit  d hud  h hide/show  m mode", (0, 255, 0)),
        ]
    else:
        lines = [
            ("MODE: [MEME REACTIONS]  (press 'm' to switch to HAND FX)", (0, 255, 255)),
            (f"showing: {shown or '-'}   raw: {raw or '-'}   hands: {d.get('hands', 0)}   elbows up: {'Y' if d.get('elbows_up') else 'n'}", (0, 255, 0)),
            (f"jaw {d.get('jaw', 0):.2f}  tongue {d.get('tongue', 0):.2f}  pucker {d.get('pucker', 0):.2f}  turn {d.get('turn', 0):.2f}  squint {d.get('squint', 0):.2f}  gesture {d.get('gesture', 0):.3f}", (0, 255, 0)),
            (f"disgust {d.get('disgust', 0):.2f} = 2x sneer {d.get('sneer', 0):.2f} + brow {d.get('brow', 0):.2f} + frown {d.get('frown', 0):.2f} + lip {d.get('lip', 0):.2f}", (0, 255, 0)),
            ("keys: q quit  d hud  h hide/show  m mode  1-9 0 - = [ p s test", (0, 255, 0)),
        ]
    for i, t in enumerate(lines):
        y = 24 + 22 * i
        cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3)
        cv2.putText(img, t, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--camera", type=int, default=0, help="webcam index (try 1 if 0 is your iPhone)")
    ap.add_argument("--no-vcam", action="store_true", help="preview only; don't start the virtual camera")
    ap.add_argument("--skip-check", action="store_true", help="skip the MediaPipe startup check")
    ap.add_argument("--size", default="1280x720", help="capture size, e.g. 1280x720 or 640x480 (lower = faster)")
    ap.add_argument("--no-flip", action="store_true", help="don't mirror the image")
    ap.add_argument("--hide", action="store_true", help="start with preview window hidden for background operation")
    ap.add_argument("--mode", choices=["meme", "hand"], default="meme", help="starting mode: 'meme' for meme reactions, 'hand' for superhero hand FX")
    args = ap.parse_args()

    model_paths = ensure_models()
    if not args.skip_check:
        preflight(model_paths["face_landmarker.task"])
    print("Assets:")
    assets = {pose: load_asset(pose) for pose in POSES}

    cap = cv2.VideoCapture(args.camera)
    if cap.isOpened() and "x" in args.size:
        w, h = args.size.lower().split("x")
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(w))
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(h))
    ok, frame = False, None
    if cap.isOpened():
        for _ in range(5):
            ok, frame = cap.read()
            if not ok:
                break
    if not ok:
        sys.exit(f"Could not read from camera {args.camera}.\n"
                 "  - try --camera 1\n"
                 "  - System Settings > Privacy & Security > Camera: allow your terminal app, then re-run")
    H, W = frame.shape[:2]
    print(f"Camera {args.camera}: {W}x{H}")

    window = "Reaction Cam  (q quit, d HUD, m mode, h hide/show, 1-9 0 - = [ p s test)"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    win_ctrl = WindowController(window, initial_hide=args.hide)
    hotkey_mgr = HotkeyManager()
    if args.hide:
        print("\n[Background Mode Active (--hide)]")
        print("  - Press 'm' in terminal or Ctrl+Alt+M anywhere to switch mode (MEME / HAND FX)")
        print("  - Press 'h' in terminal or Ctrl+Alt+H anywhere to show/hide preview window")
        print("  - Press 'q' in terminal to quit\n")

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.winmm.timeBeginPeriod(1)
        except Exception:
            pass

    vcam = None
    if not args.no_vcam:
        try:
            import pyvirtualcam
            vcam = pyvirtualcam.Camera(width=W, height=H, fps=30, fmt=pyvirtualcam.PixelFormat.BGR)
            print(f"Virtual camera: '{vcam.device}'  <- pick this camera in Zoom / Meet")
        except Exception as e:
            print(f"Virtual camera unavailable ({e}). Preview-only.")

    face_det, hand_det, pose_det = build_detectors(model_paths)
    motion = Motion()
    shown, hold, show_hud = None, 0, True
    arm = {p: 0 for p in POSES}
    shown_since = 0.0
    forced, forced_until = None, 0.0
    sm_center, sm_h = np.array([W / 2, H / 2], np.float32), H * 0.45
    t_start, last_ts = time.monotonic(), -1
    mode = args.mode
    hand_fx = HandFXRenderer()
    hand_gesture = None
    print("Running. Focus the preview window: q quit, d HUD, m mode, 1-9 0 - = [ p s test a pose")

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Camera stopped returning frames.")
                break
            if frame.shape[0] != H or frame.shape[1] != W:
                frame = cv2.resize(frame, (W, H))
            if not args.no_flip:
                frame = cv2.flip(frame, 1)

            ts = int((time.monotonic() - t_start) * 1000)
            ts = last_ts = max(ts, last_ts + 1)
            mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            fr = face_det.detect_for_video(mp_img, ts)
            hr = hand_det.detect_for_video(mp_img, ts)
            pr = pose_det.detect_for_video(mp_img, ts)
            face = Face(fr.face_landmarks[0], fr.face_blendshapes[0] if fr.face_blendshapes else None, W, H) \
                if fr.face_landmarks else None
            hands = [Hand(h, W, H) for h in hr.hand_landmarks]
            body = Body(pr.pose_landmarks[0], W, H) if pr.pose_landmarks else None

            raw, dbg = None, {}

            if mode == "hand":
                hand_gesture = hand_fx.render(frame, hands, face)
                shown = None
            else:
                hand_gesture = None
                tongue = tongue_score(frame, face, hands) if face is not None else 0.0
                gesture = motion.update(hands, face)
                raw, dbg = decide(face, hands, body, tongue, gesture)

                fired = None
                for p in POSES:
                    arm[p] = arm[p] + 1 if raw == p else 0
                    if raw == p and arm[p] >= ARM.get(p, 3):
                        fired = p
                now = time.monotonic()
                if forced and now < forced_until:
                    fired = forced
                if fired:
                    if fired != shown:
                        shown_since = now
                    shown, hold = fired, HOLD_FRAMES
                elif hold > 0:
                    hold -= 1
                else:
                    shown = None

                if face is not None:
                    sm_center = 0.7 * sm_center + 0.3 * np.array(face.center, np.float32)
                    sm_h = 0.7 * sm_h + 0.3 * face.h * FACE_SCALE

                if shown:
                    asset = assets[shown]
                    idx = asset.frame_at(int((now - shown_since) * 1000))
                    h = int(min(sm_h, H * 0.98, (W * 0.98) / asset.aspect)) // 8 * 8
                    sprite = asset.scaled(idx, max(h, 8))
                    sh, sw = sprite.shape[:2]
                    overlay(frame, sprite, int(sm_center[0] - sw / 2), int(sm_center[1] - sh / 2 - 0.05 * sh))

            win_ctrl.update()

            if vcam:
                vcam.send(frame)
                vcam.sleep_until_next_frame()

            if not win_ctrl.hidden:
                win_ctrl.created = True
                preview = frame
                if show_hud:
                    preview = frame.copy()
                    draw_hud(preview, mode, hand_gesture, shown, raw, dbg, face, hands, body)
                cv2.imshow(window, preview)
            ch = hotkey_mgr.poll()
            if ch == "q":
                break
            if ch == "d":
                show_hud = not show_hud
            elif ch == "m":
                mode = "hand" if mode == "meme" else "meme"
                print(f"\n[Mode Switched] Current Mode: {mode.upper()}")
            elif ch == "h":
                win_ctrl.toggle()
                print(f"\n[Preview Window] {'Hidden' if win_ctrl.hidden else 'Restored'}")
            elif ch and ch in TEST_KEYS:
                forced, forced_until = POSES[TEST_KEYS.index(ch)], time.monotonic() + 2.0
    finally:
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.winmm.timeEndPeriod(1)
            except Exception:
                pass
        cap.release()
        face_det.close()
        hand_det.close()
        pose_det.close()
        if vcam:
            vcam.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
