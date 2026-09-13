"""
hand_tracking.py: Real-time Hand Tracking Portal Filter Engine.
Inspired by Retrolens (syahdanfx/Retrolens) & python-handtrack (GedeAnanda/python-handtrack).

Open a magical interactive portal window between your hands.
The area inside the portal polygon dynamically applies retro & VFX filters:
(Dual-Tone, Thermal, Sketch, Glitch, Neon, Pixelate, Invert, Sepia, Cartoon, Rainbow-Wave, Edge).

Gestures:
- Spread 2 hands: Opens the portal between fingertips (Thumb & Index).
- Pinch Thumb & Pinky (or touch Index tips together): Cycle to next portal filter!
- Single hand: Opens a mini inspection lens between thumb, index, middle & pinky.
"""

import math
import random
import time
from typing import Dict, Callable
import cv2
import numpy as np


def dist(a, b):
    return float(np.hypot(a[0] - b[0], a[1] - b[1]))


class FilterBank:
    """Real-time image filter transformations applied inside the portal."""

    @staticmethod
    def dual_tone(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(gray, 120, 255, cv2.THRESH_BINARY)
        out = np.zeros_like(roi)
        out[mask == 255] = [0, 165, 255]   # Neon Orange
        out[mask == 0] = [210, 20, 220]    # Cyber Pink
        return out

    @staticmethod
    def thermal(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        return cv2.applyColorMap(gray, cv2.COLORMAP_JET)

    @staticmethod
    def sketch(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        inv = cv2.bitwise_not(gray)
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur, scale=256)
        return cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)

    @staticmethod
    def pixelate(roi: np.ndarray, block_size: int = 12) -> np.ndarray:
        h, w = roi.shape[:2]
        if h < 4 or w < 4:
            return roi
        bw = max(1, w // block_size)
        bh = max(1, h // block_size)
        small = cv2.resize(roi, (bw, bh), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

    @staticmethod
    def glitch(roi: np.ndarray) -> np.ndarray:
        h, w = roi.shape[:2]
        if h < 4 or w < 4:
            return roi
        b, g, r = cv2.split(roi)
        shift = max(4, w // 25)
        r_shifted = np.roll(r, shift, axis=1)
        b_shifted = np.roll(b, -shift, axis=1)
        out = cv2.merge([b_shifted, g, r_shifted])
        # Random scanline slices
        for _ in range(2):
            y_scan = random.randint(0, h - 1)
            out[y_scan:y_scan + 2, :] = np.random.randint(0, 255, (min(2, h - y_scan), w, 3), dtype=np.uint8)
        return out

    @staticmethod
    def neon(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blur, 40, 130)
        edges_bgr = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        # Tint glowing edges to electric cyan
        edges_bgr[np.where((edges_bgr == [255, 255, 255]).all(axis=2))] = [255, 255, 0]
        kernel = np.ones((3, 3), np.uint8)
        return cv2.dilate(edges_bgr, kernel, iterations=1)

    @staticmethod
    def invert(roi: np.ndarray) -> np.ndarray:
        return cv2.bitwise_not(roi)

    @staticmethod
    def sepia(roi: np.ndarray) -> np.ndarray:
        kernel = np.array([
            [0.272, 0.534, 0.131],
            [0.349, 0.686, 0.168],
            [0.393, 0.769, 0.189]
        ])
        filtered = cv2.transform(roi, kernel)
        return np.clip(filtered, 0, 255).astype(np.uint8)

    @staticmethod
    def cartoon(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        gray_blur = cv2.medianBlur(gray, 5)
        edges = cv2.adaptiveThreshold(gray_blur, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(roi, 9, 200, 200)
        return cv2.bitwise_and(color, cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR))

    @staticmethod
    def edge(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 140)
        colored = cv2.applyColorMap(edges, cv2.COLORMAP_SUMMER)
        return cv2.bitwise_and(colored, colored, mask=edges)

    @staticmethod
    def rainbow_wave(roi: np.ndarray) -> np.ndarray:
        h, w = roi.shape[:2]
        t = time.time() * 4.0
        x_coords, y_coords = np.meshgrid(np.arange(w), np.arange(h))
        pattern = np.sin((x_coords + y_coords) * 0.04 + t) * 127 + 128
        rainbow = cv2.applyColorMap(pattern.astype(np.uint8), cv2.COLORMAP_HSV)
        return cv2.addWeighted(roi, 0.35, rainbow, 0.65, 0)

    @staticmethod
    def blur(roi: np.ndarray) -> np.ndarray:
        return cv2.GaussianBlur(roi, (25, 25), 0)

    @staticmethod
    def red_channel(roi: np.ndarray) -> np.ndarray:
        b, g, r = cv2.split(roi)
        zeros = np.zeros_like(b)
        return cv2.merge([zeros, zeros, r])

    @staticmethod
    def galaxy(roi: np.ndarray) -> np.ndarray:
        """Procedural cosmic galaxy / nebula filter (from python-handtrack)."""
        h, w = roi.shape[:2]
        # Create deep space nebula background with purple/blue tint
        nebula = np.zeros((h, w, 3), dtype=np.uint8)
        nebula[:, :] = (35, 10, 45) # Deep cosmic purple

        # Add pulsating cosmic glow
        t = time.time() * 2.0
        x_c, y_c = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
        dist_c = np.sqrt(x_c ** 2 + y_c ** 2)
        glow = np.clip(np.sin(dist_c * 4.0 - t) * 60 + 60, 0, 120).astype(np.uint8)
        nebula[:, :, 0] = cv2.add(nebula[:, :, 0], glow) # Blue glow
        nebula[:, :, 2] = cv2.add(nebula[:, :, 2], (glow * 0.8).astype(np.uint8)) # Red/Pink glow

        # High-contrast subject extraction
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, subject_mask = cv2.threshold(gray, 70, 255, cv2.THRESH_BINARY)
        subject_mask_3c = cv2.cvtColor(subject_mask, cv2.COLOR_GRAY2BGR)

        # Composite subject with neon tint onto cosmic nebula
        subject_tinted = cv2.applyColorMap(gray, cv2.COLORMAP_MAGMA)
        out = np.where(subject_mask_3c == 255, subject_tinted, nebula)
        return cv2.addWeighted(roi, 0.25, out, 0.75, 0)

    @staticmethod
    def mono(roi: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


class Spark:
    """Persistent particle spark moving smoothly along the portal boundary."""
    def __init__(self, edge_idx: int = 0):
        self.edge_idx = edge_idx
        self.t = random.random()
        self.speed = random.uniform(0.15, 0.40) * random.choice([1, -1])
        self.offset = random.uniform(-4.0, 4.0)
        self.life = 1.0
        self.decay = random.uniform(0.015, 0.030)
        self.color = random.choice([(0, 255, 255), (255, 255, 255), (255, 140, 255), (255, 240, 100)])
        self.size = random.randint(1, 2)

    def update(self, dt: float) -> bool:
        self.t = (self.t + self.speed * dt) % 1.0
        self.life -= self.decay
        return self.life > 0.0


def adaptive_smooth_points(new_pts: np.ndarray, prev_pts: np.ndarray) -> np.ndarray:
    """
    Velocity-adaptive exponential smoothing filter:
    - Subtle sensor jitter (< 2px): alpha ~ 0.16 (buttery smooth, zero vibration)
    - Gentle motion (2-15px): alpha ~ 0.25 - 0.45
    - Fast hand movement (> 25px): alpha ~ 0.80 (rapid tracking, zero delay)
    """
    if prev_pts is None or len(prev_pts) != len(new_pts):
        return new_pts.astype(np.float32)
    smoothed = np.zeros_like(new_pts, dtype=np.float32)
    for i in range(len(new_pts)):
        p_new = new_pts[i].astype(np.float32)
        p_old = prev_pts[i].astype(np.float32)
        dist_px = float(np.linalg.norm(p_new - p_old))
        t = np.clip((dist_px - 1.5) / 24.0, 0.0, 1.0)
        alpha = 0.16 + 0.64 * (t ** 1.4)
        smoothed[i] = alpha * p_new + (1.0 - alpha) * p_old
    return smoothed


class HandTrackingEngine:
    """
    Ultra-Smooth RetroLens & Python-Handtrack Portal Filter Engine.
    - Velocity-adaptive EMA smoothing eliminates landmark sensor jitter.
    - Strict physical corner topology prevents polygon vertex jumping / twisting.
    - Grace frames buffer eliminates 1-frame tracking flicker.
    - Silky filter cross-dissolve and persistent edge sparks.
    - 2D Quad Mode + 3D Dual-Mesh Mode + Single Hand Mini Lens.
    """

    def __init__(self, frame_w, frame_h):
        self.frame_w = frame_w
        self.frame_h = frame_h

        self.filters: Dict[str, Callable[[np.ndarray], np.ndarray]] = {
            "DUAL-TONE": FilterBank.dual_tone,
            "THERMAL": FilterBank.thermal,
            "SKETCH": FilterBank.sketch,
            "GLITCH": FilterBank.glitch,
            "NEON": FilterBank.neon,
            "PIXELATE": FilterBank.pixelate,
            "GALAXY": FilterBank.galaxy,
            "CARTOON": FilterBank.cartoon,
            "RAINBOW-WAVE": FilterBank.rainbow_wave,
            "BLUR": FilterBank.blur,
            "INVERT": FilterBank.invert,
            "SEPIA": FilterBank.sepia,
            "RED-CHANNEL": FilterBank.red_channel,
            "EDGE": FilterBank.edge,
            "MONO": FilterBank.mono,
        }
        self.filter_keys = list(self.filters.keys())
        self.current_filter_idx = 0
        self.prev_filter_name = None
        self.filter_blend_progress = 1.0
        self.is_3d_mode = False

        # State and smoothing
        self.corners_smooth = None
        self.corners_smooth_b = None
        self.anchor_dots_smooth = None
        self.gesture_triggered = False
        self.last_gesture_time = 0.0
        self.last_fist_toggle_time = 0.0
        self.last_frame_time = time.monotonic()
        self.portal_active = False

        # Grace frames & fade transitions
        self.grace_frames = 0
        self.portal_alpha = 0.0

        # Persistent particle sparks system
        self.sparks: List[Spark] = []

    @property
    def active_filter_name(self) -> str:
        return self.filter_keys[self.current_filter_idx]

    @property
    def secondary_filter_name(self) -> str:
        return self.filter_keys[(self.current_filter_idx + 1) % len(self.filter_keys)]

    def next_filter(self, step: int = 1):
        """Cycles to next portal filter with silky cross-fade."""
        self.prev_filter_name = self.active_filter_name
        self.current_filter_idx = (self.current_filter_idx + step) % len(self.filter_keys)
        self.filter_blend_progress = 0.0 # Trigger cross-dissolve
        name = self.active_filter_name
        print(f"\n[Portal Filter] Active: {name}")
        return name

    def toggle_3d_mode(self) -> bool:
        """Toggles between 2D Single Quad Portal and 3D Dual-Mesh Portal."""
        self.is_3d_mode = not self.is_3d_mode
        self.corners_smooth = None
        self.corners_smooth_b = None
        self.anchor_dots_smooth = None
        print(f"\n[Portal Mode] {'3D Dual-Mesh Mode' if self.is_3d_mode else '2D Single Quad Mode'}")
        return self.is_3d_mode

    def reset(self):
        """Resets portal state."""
        self.corners_smooth = None
        self.corners_smooth_b = None
        self.anchor_dots_smooth = None
        self.portal_active = False
        self.grace_frames = 0
        self.portal_alpha = 0.0
        self.sparks.clear()
        print("\n[Portal Filter] Portal reset.")

    def _render_polygon_portal(self, frame: np.ndarray, poly_pts: np.ndarray, filter_name: str, label: str = None, dt: float = 0.033) -> np.ndarray:
        """Renders filtered VFX within a polygon boundary, with glowing borders and persistent sparks."""
        H, W = frame.shape[:2]
        bx, by, bw, bh = cv2.boundingRect(poly_pts)
        bx, by = max(0, bx), max(0, by)
        bw, bh = min(W - bx, bw), min(H - by, bh)

        if bw < 15 or bh < 15:
            return frame

        roi = frame[by:by + bh, bx:bx + bw].copy()

        # 1. Apply active filter function (with silky cross-dissolve if switching)
        filter_fn = self.filters.get(filter_name, FilterBank.dual_tone)
        if self.filter_blend_progress < 1.0 and self.prev_filter_name and (self.prev_filter_name in self.filters):
            old_fn = self.filters[self.prev_filter_name]
            try:
                f_old = old_fn(roi)
                f_new = filter_fn(roi)
                filtered_roi = cv2.addWeighted(f_new, self.filter_blend_progress, f_old, 1.0 - self.filter_blend_progress, 0)
            except Exception:
                filtered_roi = filter_fn(roi)
            self.filter_blend_progress = min(1.0, self.filter_blend_progress + 0.20)
        else:
            try:
                filtered_roi = filter_fn(roi)
            except Exception:
                filtered_roi = roi

        # Smooth portal fade-in / fade-out blend
        if self.portal_alpha < 0.98:
            filtered_roi = cv2.addWeighted(filtered_roi, self.portal_alpha, roi, 1.0 - self.portal_alpha, 0)

        # 2. Fast integer mask compositing
        mask = np.zeros((bh, bw), dtype=np.uint8)
        poly_roi = poly_pts - [bx, by]
        cv2.fillPoly(mask, [poly_roi], 255)

        mask_3c = cv2.merge([mask, mask, mask])
        bg = cv2.bitwise_and(roi, cv2.bitwise_not(mask_3c))
        fg = cv2.bitwise_and(filtered_roi, mask_3c)
        frame[by:by + bh, bx:bx + bw] = cv2.add(bg, fg)

        # 3. Double-layer Glowing Portal Border (antialiased)
        cv2.polylines(frame, [poly_pts], isClosed=True, color=(0, 200, 255), thickness=3, lineType=cv2.LINE_AA)
        cv2.polylines(frame, [poly_pts], isClosed=True, color=(255, 255, 255), thickness=1, lineType=cv2.LINE_AA)

        # 4. Persistent Particle Sparks System
        num_pts = len(poly_pts)
        if len(self.sparks) < 16:
            for _ in range(2):
                self.sparks.append(Spark(edge_idx=random.randint(0, num_pts - 1)))

        alive_sparks = []
        for spark in self.sparks:
            if spark.update(dt):
                alive_sparks.append(spark)
                idx = spark.edge_idx % num_pts
                p1 = poly_pts[idx]
                p2 = poly_pts[(idx + 1) % num_pts]

                # Position along edge + normal vector offset
                dx, dy = float(p2[0] - p1[0]), float(p2[1] - p1[1])
                seg_len = max(1.0, float(np.hypot(dx, dy)))
                nx, ny = -dy / seg_len, dx / seg_len

                sx = int(p1[0] * (1.0 - spark.t) + p2[0] * spark.t + nx * spark.offset)
                sy = int(p1[1] * (1.0 - spark.t) + p2[1] * spark.t + ny * spark.offset)

                if 0 <= sx < W and 0 <= sy < H:
                    cv2.circle(frame, (sx, sy), spark.size, spark.color, -1, lineType=cv2.LINE_AA)
        self.sparks = alive_sparks

        # 5. Stylish Portal Header Tag
        if label:
            header_x = max(10, int(poly_pts[0][0]))
            header_y = max(25, int(poly_pts[0][1]) - 12)
            cv2.putText(frame, label, (header_x, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(frame, label, (header_x, header_y), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 1, cv2.LINE_AA)

        return frame

    def update_and_render(self, frame: np.ndarray, hands) -> np.ndarray:
        """
        Main execution pipeline with butter-smooth tracking:
        1. Checks pinch gestures to switch filter (Thumb + Pinky pinch or 2 Index tips touching).
        2. Checks dual-fist gesture to toggle 3D Dual-Mesh mode.
        3. Constructs topologically stable polygon vertices.
        4. Applies velocity-adaptive smoothing and renders portal filter(s).
        5. Renders smoothed fingertip anchor dots.
        """
        H, W = frame.shape[:2]
        now = time.monotonic()
        dt = max(0.001, min(0.1, now - self.last_frame_time))
        self.last_frame_time = now

        # 1. Gesture detection for filter switching
        change_filter = False
        fist_count = 0

        if len(hands) >= 2:
            # Check if index tips touch each other
            idx0 = hands[0].index
            idx1 = hands[1].index
            if dist(idx0, idx1) < 40.0:
                change_filter = True

        for h in hands:
            # Check Thumb & Pinky pinch on either hand
            thumb = h.thumb
            pinky = h.pinky
            if dist(thumb, pinky) < 42.0:
                change_filter = True

            # Fist detection (tips clustered near wrist)
            wrist = np.array(h.wrist, dtype=np.float32)
            tips = [h.index, h.middle, h.ring, h.pinky]
            mean_dist = float(np.mean([np.linalg.norm(np.array(t, dtype=np.float32) - wrist) for t in tips]))
            if mean_dist < 80.0:
                fist_count += 1

        # Dual fist toggles 3D Dual-Mesh Mode
        if fist_count == 2 and (now - self.last_fist_toggle_time > 1.2):
            self.toggle_3d_mode()
            self.last_fist_toggle_time = now

        # Debounce gesture switching
        if change_filter:
            if not self.gesture_triggered and (now - self.last_gesture_time > 0.40):
                self.next_filter(1)
                self.gesture_triggered = True
                self.last_gesture_time = now
        else:
            self.gesture_triggered = False

        # 2. Extract fingertips with dedicated physical corner topology
        anchor_dots = []
        has_hands = False

        if self.is_3d_mode and len(hands) >= 2:
            has_hands = True
            sorted_hands = sorted(hands, key=lambda h: h.palm[0])
            h1, h2 = sorted_hands[0], sorted_hands[-1]

            t1 = [h1.thumb, h1.index, h1.middle, h1.ring, h1.pinky]
            t2 = [h2.thumb, h2.index, h2.middle, h2.ring, h2.pinky]

            poly_upper = np.array([t1[0], t1[1], t1[2], t2[2], t2[1], t2[0]], dtype=np.float32)
            poly_lower = np.array([t1[2], t1[3], t1[4], t2[4], t2[3], t2[2]], dtype=np.float32)

            self.corners_smooth = adaptive_smooth_points(poly_upper, self.corners_smooth)
            self.corners_smooth_b = adaptive_smooth_points(poly_lower, self.corners_smooth_b)

            anchor_dots = [h1.thumb, h1.index, h1.middle, h1.ring, h1.pinky, h2.thumb, h2.index, h2.middle, h2.ring, h2.pinky]

        elif len(hands) >= 2:
            has_hands = True
            sorted_hands = sorted(hands, key=lambda h: h.palm[0])
            h_left, h_right = sorted_hands[0], sorted_hands[-1]

            # Physical topological sorting for left hand:
            # Upper finger is ALWAYS Top-Left, lower finger is ALWAYS Bottom-Left
            l_th = np.array(h_left.thumb, dtype=np.float32)
            l_idx = np.array(h_left.index, dtype=np.float32)
            if l_idx[1] < l_th[1]:
                p_tl, p_bl = l_idx, l_th
            else:
                p_tl, p_bl = l_th, l_idx

            # Physical topological sorting for right hand:
            # Upper finger is ALWAYS Top-Right, lower finger is ALWAYS Bottom-Right
            r_th = np.array(h_right.thumb, dtype=np.float32)
            r_idx = np.array(h_right.index, dtype=np.float32)
            if r_idx[1] < r_th[1]:
                p_tr, p_br = r_idx, r_th
            else:
                p_tr, p_br = r_th, r_idx

            target_poly = np.array([p_tl, p_tr, p_br, p_bl], dtype=np.float32)
            self.corners_smooth = adaptive_smooth_points(target_poly, self.corners_smooth)
            anchor_dots = [h_left.thumb, h_left.index, h_right.thumb, h_right.index]

        elif len(hands) == 1:
            has_hands = True
            h = hands[0]
            pts = [
                np.array(h.thumb, dtype=np.float32),
                np.array(h.index, dtype=np.float32),
                np.array(h.middle, dtype=np.float32),
                np.array(h.pinky, dtype=np.float32),
            ]
            # Angular sort around centroid for convex loop
            centroid = np.mean(pts, axis=0)
            pts_sorted = sorted(pts, key=lambda p: math.atan2(p[1] - centroid[1], p[0] - centroid[0]))
            target_poly = np.array(pts_sorted, dtype=np.float32)
            self.corners_smooth = adaptive_smooth_points(target_poly, self.corners_smooth)
            anchor_dots = [h.thumb, h.index, h.middle, h.pinky]

        # 3. Grace frames & smooth fade transition
        if has_hands:
            self.grace_frames = 6
            target_portal_alpha = 1.0
        else:
            if self.grace_frames > 0:
                self.grace_frames -= 1
                target_portal_alpha = 1.0
            else:
                target_portal_alpha = 0.0

        self.portal_alpha += (target_portal_alpha - self.portal_alpha) * 0.32

        # 4. Render portal if active
        if self.portal_alpha > 0.03 and (self.corners_smooth is not None):
            self.portal_active = True
            if self.is_3d_mode and (self.corners_smooth_b is not None):
                frame = self._render_polygon_portal(frame, self.corners_smooth.astype(np.int32), self.active_filter_name, f"PORTAL A: {self.active_filter_name}", dt)
                frame = self._render_polygon_portal(frame, self.corners_smooth_b.astype(np.int32), self.secondary_filter_name, f"PORTAL B: {self.secondary_filter_name}", dt)
            else:
                frame = self._render_polygon_portal(frame, self.corners_smooth.astype(np.int32), self.active_filter_name, f"PORTAL: {self.active_filter_name}", dt)
        else:
            self.portal_active = False
            if self.portal_alpha <= 0.03:
                self.corners_smooth = None
                self.corners_smooth_b = None
                self.anchor_dots_smooth = None

        # 5. Draw smoothed glowing anchor dots on fingertips
        if anchor_dots:
            dots_np = np.array(anchor_dots, dtype=np.float32)
            self.anchor_dots_smooth = adaptive_smooth_points(dots_np, self.anchor_dots_smooth)
            for pt in self.anchor_dots_smooth:
                px, py = int(pt[0]), int(pt[1])
                cv2.circle(frame, (px, py), 6, (0, 255, 255), cv2.FILLED, lineType=cv2.LINE_AA)
                cv2.circle(frame, (px, py), 8, (255, 255, 255), 1, lineType=cv2.LINE_AA)
        else:
            self.anchor_dots_smooth = None

        return frame
