"""
background.py: Real-time background removal, blur, and custom virtual background
using MediaPipe Selfie Segmenter and ultra-fast cv2.blendLinear.

Pipeline order:
Webcam -> Segmentation -> Background Processing -> Meme/Hand FX -> Virtual Camera
"""

import os
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_tasks
from mediapipe.tasks.python import vision

BG_MODES = ["original", "remove", "blur", "custom"]


class BackgroundEngine:
    """Handles real-time selfie segmentation and background replacement."""

    def __init__(self, model_path, custom_bg_path="assets/background.jpeg", initial_mode="original"):
        self.mode = initial_mode if initial_mode in BG_MODES else "original"
        
        # Prefer the landscape model for 16:9 widescreen webcam if available
        base_dir = os.path.dirname(model_path) if model_path else "models"
        landscape_path = os.path.join(base_dir, "selfie_segmenter_landscape.tflite")
        if os.path.exists(landscape_path):
            self.model_path = landscape_path
        else:
            self.model_path = model_path

        self.custom_bg_path = custom_bg_path
        self.custom_raw = None
        self.cached_custom_bg = None
        self.cached_size = None
        self.smooth_mask = None

        self.segmenter = None
        self._init_segmenter()
        self.load_custom_bg(custom_bg_path)

    def _init_segmenter(self):
        opts = vision.ImageSegmenterOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=self.model_path),
            running_mode=vision.RunningMode.VIDEO,
            output_confidence_masks=True,
        )
        self.segmenter = vision.ImageSegmenter.create_from_options(opts)

    def load_custom_bg(self, path):
        """Load and cache the custom background image."""
        self.custom_bg_path = path
        if path and os.path.exists(path):
            self.custom_raw = cv2.imread(path)
            self.cached_custom_bg = None
            self.cached_size = None
            print(f"[BackgroundEngine] Loaded custom background: {path}")
        else:
            self.custom_raw = None
            self.cached_custom_bg = None
            print(f"[BackgroundEngine] Custom background file not found: {path}")

    def cycle_mode(self):
        """Cycle to the next background mode: original -> remove -> blur -> custom -> original."""
        idx = BG_MODES.index(self.mode) if self.mode in BG_MODES else 0
        self.mode = BG_MODES[(idx + 1) % len(BG_MODES)]
        self.smooth_mask = None
        return self.mode

    def set_mode(self, mode):
        if mode in BG_MODES:
            self.mode = mode
        elif mode in ("green", "transparent"):
            self.mode = "remove"
        elif mode in ("none", "off"):
            self.mode = "original"
        self.smooth_mask = None
        return self.mode

    def _get_custom_bg(self, target_w, target_h):
        """Scale and center-crop the custom background image to match target dimensions."""
        if self.cached_size == (target_w, target_h) and self.cached_custom_bg is not None:
            return self.cached_custom_bg

        if self.custom_raw is None:
            bg = np.zeros((target_h, target_w, 3), dtype=np.uint8)
            bg[:] = (40, 35, 30)
            self.cached_custom_bg = bg
            self.cached_size = (target_w, target_h)
            return bg

        raw_h, raw_w = self.custom_raw.shape[:2]
        scale = max(target_w / raw_w, target_h / raw_h)
        new_w, new_h = int(raw_w * scale), int(raw_h * scale)
        resized = cv2.resize(self.custom_raw, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        x0 = (new_w - target_w) // 2
        y0 = (new_h - target_h) // 2
        cropped = resized[y0:y0 + target_h, x0:x0 + target_w]

        self.cached_custom_bg = cropped
        self.cached_size = (target_w, target_h)
        return self.cached_custom_bg

    def process(self, frame, mp_img, ts, face=None, hands=None):
        """
        Process the frame through background segmentation and replacement.
        Must be called BEFORE Meme Mode and Hand FX overlays.
        """
        if self.mode == "original":
            self.smooth_mask = None
            return frame

        h, w = frame.shape[:2]

        # 1. Run MediaPipe segmentation (~7ms)
        res = self.segmenter.segment_for_video(mp_img, ts)
        if not res.confidence_masks:
            return frame

        # Raw confidence mask [0.0, 1.0] from MediaPipe
        conf = res.confidence_masks[0].numpy_view().copy()

        # 2. Face Guarantee: Ensure face region is 100% solid (prevents face turning green)
        if face is not None:
            if getattr(face, "pts", None) is not None:
                hull = cv2.convexHull(face.pts.astype(np.int32))
                cv2.fillConvexPoly(conf, hull, 1.0)
            elif getattr(face, "box", None) is not None:
                fx0, fy0, fx1, fy1 = face.box
                fx0, fy0 = max(0, fx0), max(0, fy0)
                fx1, fy1 = min(w, fx1), min(h, fy1)
                cx, cy = (fx0 + fx1) // 2, (fy0 + fy1) // 2
                ax, ay = max((fx1 - fx0) // 2, 10), max((fy1 - fy0) // 2, 10)
                cv2.ellipse(conf, (cx, cy), (ax, ay), 0, 0, 360, 1.0, -1)

        # 3. Hand Guarantee: Ensure hands and fingers are 100% solid
        if hands:
            for hnd in hands:
                if getattr(hnd, "pts", None) is not None:
                    hull = cv2.convexHull(hnd.pts.astype(np.int32))
                    cv2.fillConvexPoly(conf, hull, 1.0)
                cx, cy = int(hnd.palm[0]), int(hnd.palm[1])
                rad = int(max(getattr(hnd, "w", 30), getattr(hnd, "h", 30)) * 0.75)
                cv2.circle(conf, (cx, cy), max(rad, 25), 1.0, -1)

        # 4. Solidify Person Core & Narrow Feathering Transition:
        # Anything >= 0.50 is 100% person with ZERO green leak.
        # Transition is restricted to a tight 0.35 -> 0.50 perimeter band.
        t = np.clip((conf - 0.35) / 0.15, 0.0, 1.0)
        # Smoothstep curve for natural photographic falloff:
        raw_mask = t * t * (3.0 - 2.0 * t)

        # 5. Spatial Gaussian Blur for soft, anti-aliased edge blending (Instantaneous: ZERO ghosting/shadow lag)
        w1 = cv2.GaussianBlur(raw_mask, (5, 5), 0)
        w2 = 1.0 - w1

        # 7. Prepare background image
        if self.mode == "remove":
            # Chroma Green (0, 255, 0)
            bg = np.zeros_like(frame)
            bg[:] = (0, 255, 0)
        elif self.mode == "blur":
            # Fast bokeh blur (1.8ms): downscale 4x -> GaussianBlur -> upscale
            small = cv2.resize(frame, (max(w // 4, 16), max(h // 4, 16)))
            blurred_small = cv2.GaussianBlur(small, (21, 21), 0)
            bg = cv2.resize(blurred_small, (w, h), interpolation=cv2.INTER_LINEAR)
        elif self.mode == "custom":
            bg = self._get_custom_bg(w, h)
        else:
            return frame

        # 8. Fast native C++ alpha blend (1.5ms)
        out = cv2.blendLinear(frame, bg, w1, w2)
        return out

    def close(self):
        if self.segmenter:
            try:
                self.segmenter.close()
            except Exception:
                pass
            self.segmenter = None
