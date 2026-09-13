"""
hand_fx.py — Real-time superhero & hand gesture effects for itsgiving.

Supported Gestures & Effects:
  1. Spiderman (🤟): Dynamic spiderweb shooting from wrist with concentric web arcs & "THWIP!" badge.
  2. Kamehameha / Energy Ball (👐): Glowing plasma sphere with animated electric lightning between palms.
  3. Iron Man Repulsor (✋): High-tech glowing repulsor core with shockwave pulse on open palm.
  4. Finger Gun (👉): Blaster laser beam & muzzle flash with "BANG!" comic text.
  5. Peace Sign (✌️): Floating animated sparkles, pastel bubbles & stars.
"""
import math
import random
import time
import cv2
import numpy as np


def draw_glow_circle(overlay, center, radius, color, thickness=-1):
    """Draw a circle on an overlay for alpha blending."""
    cv2.circle(overlay, (int(center[0]), int(center[1])), int(radius), color, thickness, cv2.LINE_AA)


def draw_comic_badge(img, text, pos, bg_color=(0, 0, 220), text_color=(255, 255, 255), scale=0.8):
    """Draw a comic book style action badge with slant box and border."""
    x, y = int(pos[0]), int(pos[1])
    (tw, th), baseline = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, 2)
    pad = 8
    pts = np.array([
        [x - pad, y - th - pad],
        [x + tw + pad + 10, y - th - pad - 4],
        [x + tw + pad, y + pad],
        [x - pad - 10, y + pad + 4],
    ], np.int32)
    cv2.fillPoly(img, [pts], (0, 0, 0))
    cv2.fillPoly(img, [pts - [2, 2]], bg_color)
    cv2.polylines(img, [pts - [2, 2]], True, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_DUPLEX, scale, text_color, 2, cv2.LINE_AA)


class HandFXRenderer:
    def __init__(self):
        self.frame_count = 0
        self.particles = []
        self.start_time = time.monotonic()

    def update(self):
        self.frame_count += 1

    def draw_spiderman(self, frame, hand, fw):
        """Render Spiderman web shooter (🤟) with procedural web net and THWIP! badge."""
        H, W = frame.shape[:2]
        wrist = hand.wrist
        direction = hand.middle - wrist
        d_len = max(np.hypot(direction[0], direction[1]), 1.0)
        ux, uy = direction[0] / d_len, direction[1] / d_len

        # Perpendicular vector
        px, py = -uy, ux

        # Web origins and targets
        ox, oy = wrist[0], wrist[1]
        base_reach = max(fw * 2.2, 180.0)

        # Draw 7 radiating web strands
        angles = [-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6]
        endpoints = []
        for a in angles:
            cos_a, sin_a = math.cos(a), math.sin(a)
            # rotate direction vector
            rx = ux * cos_a - uy * sin_a
            ry = ux * sin_a + uy * cos_a
            reach = base_reach * (1.0 + 0.15 * math.cos(self.frame_count * 0.3 + a))
            tx = np.clip(ox + rx * reach, 0, W - 1)
            ty = np.clip(oy + ry * reach, 0, H - 1)
            endpoints.append((tx, ty))

        # Alpha overlay for glowing white web
        overlay = frame.copy()

        # Radial lines
        for ep in endpoints:
            cv2.line(overlay, (int(ox), int(oy)), (int(ep[0]), int(ep[1])), (255, 255, 255), 2, cv2.LINE_AA)

        # Concentric connecting web arcs
        for r_step in [0.25, 0.50, 0.75, 1.0]:
            arc_pts = []
            for ep in endpoints:
                ax = ox + (ep[0] - ox) * r_step
                ay = oy + (ep[1] - oy) * r_step
                arc_pts.append([int(ax), int(ay)])
            if len(arc_pts) > 1:
                cv2.polylines(overlay, [np.array(arc_pts, np.int32)], False, (240, 240, 255), 2, cv2.LINE_AA)

        # Central web spinneret burst
        cv2.circle(overlay, (int(ox), int(oy)), int(fw * 0.25), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, (int(ox), int(oy)), int(fw * 0.35), (0, 0, 255), 3, cv2.LINE_AA)

        # Blend web overlay
        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        # Badge: THWIP!
        badge_x = int(np.clip(ox + px * fw * 0.9, 30, W - 140))
        badge_y = int(np.clip(oy + py * fw * 0.9, 40, H - 30))
        draw_comic_badge(frame, "THWIP!", (badge_x, badge_y), bg_color=(30, 30, 220), text_color=(255, 255, 255), scale=0.9)

    def draw_kamehameha(self, frame, hand_a, hand_b, fw):
        """Render glowing plasma energy orb with lightning bolts between two open palms (👐)."""
        H, W = frame.shape[:2]
        center = ((hand_a.palm + hand_b.palm) / 2)
        cx, cy = int(center[0]), int(center[1])
        hand_dist = float(np.hypot(hand_a.palm[0] - hand_b.palm[0], hand_a.palm[1] - hand_b.palm[1]))

        # Pulse animation
        pulse = 1.0 + 0.12 * math.sin(self.frame_count * 0.4)
        radius = int(max(fw * 0.55, hand_dist * 0.45) * pulse)

        overlay = frame.copy()

        # Outer electric blue glow
        draw_glow_circle(overlay, (cx, cy), radius * 1.5, (255, 200, 0), -1)  # Cyan aura
        draw_glow_circle(overlay, (cx, cy), radius * 1.1, (255, 120, 0), -1)  # Blue plasma
        draw_glow_circle(overlay, (cx, cy), radius * 0.65, (255, 255, 200), -1)  # Core
        draw_glow_circle(overlay, (cx, cy), radius * 0.35, (255, 255, 255), -1)  # White center

        # Lightning arcs connecting palms to center
        for h in [hand_a, hand_b]:
            px, py = h.palm[0], h.palm[1]
            pts = [(int(px), int(py))]
            steps = 4
            for s in range(1, steps):
                t = s / steps
                lx = px + (cx - px) * t + random.uniform(-fw * 0.15, fw * 0.15)
                ly = py + (cy - py) * t + random.uniform(-fw * 0.15, fw * 0.15)
                pts.append((int(lx), int(ly)))
            pts.append((cx, cy))
            cv2.polylines(overlay, [np.array(pts, np.int32)], False, (255, 255, 255), 2, cv2.LINE_AA)

        # Composite aura
        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Badge
        badge_y = max(35, cy - radius - 20)
        draw_comic_badge(frame, "KAMEHAMEHA!", (cx - 100, badge_y), bg_color=(200, 100, 0), text_color=(255, 255, 255), scale=0.85)

    def draw_repulsor(self, frame, hand, fw):
        """Render Iron Man repulsor blast (✋) on open palm."""
        H, W = frame.shape[:2]
        cx, cy = int(hand.palm[0]), int(hand.palm[1])
        pulse = 1.0 + 0.15 * math.sin(self.frame_count * 0.5)
        r = int(fw * 0.35 * pulse)

        overlay = frame.copy()
        draw_glow_circle(overlay, (cx, cy), r * 1.8, (255, 180, 0), -1)  # Cyan aura
        draw_glow_circle(overlay, (cx, cy), r * 1.2, (255, 255, 120), -1)
        draw_glow_circle(overlay, (cx, cy), r * 0.6, (255, 255, 255), -1)

        # Shockwave ring
        wave_r = int((r * 1.5 + (self.frame_count * 4) % (r * 2)))
        cv2.circle(overlay, (cx, cy), wave_r, (255, 255, 200), 3, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        draw_comic_badge(frame, "REPULSOR", (cx - 60, cy - r - 25), bg_color=(0, 140, 255), text_color=(255, 255, 255), scale=0.7)

    def draw_finger_gun(self, frame, hand, fw):
        """Render Finger Gun laser beam & muzzle flash (👉) with BANG! badge."""
        H, W = frame.shape[:2]
        tip = hand.index
        base = hand.pts[6]  # Index knuckle
        dx, dy = tip[0] - base[0], tip[1] - base[1]
        length = max(np.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length

        # Shoot beam to edge of screen
        reach = max(W, H) * 1.2
        target_x = int(tip[0] + ux * reach)
        target_y = int(tip[1] + uy * reach)

        overlay = frame.copy()
        # Thick outer neon laser beam
        cv2.line(overlay, (int(tip[0]), int(tip[1])), (target_x, target_y), (0, 0, 255), 8, cv2.LINE_AA)
        # Intense inner beam
        cv2.line(overlay, (int(tip[0]), int(tip[1])), (target_x, target_y), (150, 255, 255), 3, cv2.LINE_AA)

        # Muzzle flash starburst
        mx, my = int(tip[0]), int(tip[1])
        draw_glow_circle(overlay, (mx, my), int(fw * 0.3), (0, 160, 255), -1)
        draw_glow_circle(overlay, (mx, my), int(fw * 0.15), (255, 255, 255), -1)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        draw_comic_badge(frame, "BANG!", (mx + int(ux * 40) - 20, my + int(uy * 40) - 20),
                         bg_color=(0, 0, 240), text_color=(255, 255, 0), scale=0.85)

    def draw_peace_sparkles(self, frame, hand, fw):
        """Render animated cute sparkles, floating stars and bubbles for peace sign (✌️)."""
        H, W = frame.shape[:2]
        center = (hand.index + hand.middle) / 2
        cx, cy = center[0], center[1]

        # Draw floating stars around fingertips
        colors = [(0, 220, 255), (255, 120, 255), (100, 255, 255), (255, 255, 100)]
        for i in range(5):
            angle = (self.frame_count * 0.08 + i * (2 * math.pi / 5))
            dist_r = fw * (0.4 + 0.15 * math.sin(self.frame_count * 0.15 + i))
            sx = int(cx + math.cos(angle) * dist_r)
            sy = int(cy + math.sin(angle) * dist_r)
            if 0 <= sx < W and 0 <= sy < H:
                c = colors[i % len(colors)]
                star_size = int(6 + 3 * math.sin(self.frame_count * 0.2 + i))
                cv2.circle(frame, (sx, sy), star_size, c, -1, cv2.LINE_AA)
                cv2.circle(frame, (sx, sy), max(1, star_size // 2), (255, 255, 255), -1, cv2.LINE_AA)
                # Cross glint
                cv2.line(frame, (sx - star_size * 2, sy), (sx + star_size * 2, sy), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(frame, (sx, sy - star_size * 2), (sx, sy + star_size * 2), (255, 255, 255), 1, cv2.LINE_AA)

        draw_comic_badge(frame, "PEACE!", (int(cx - 35), int(cy - fw * 0.5)),
                         bg_color=(200, 60, 220), text_color=(255, 255, 255), scale=0.7)

    def render(self, frame, hands, face):
        """Main rendering entrypoint. Returns name of primary gesture detected, or None."""
        self.update()
        fw = face.w if face is not None else 120.0
        primary = None

        # Check two-hand Kamehameha first
        if len(hands) >= 2:
            h1, h2 = hands[0], hands[1]
            hand_dist = float(np.hypot(h1.palm[0] - h2.palm[0], h1.palm[1] - h2.palm[1]))
            if h1.open and h2.open and hand_dist < 2.5 * fw:
                self.draw_kamehameha(frame, h1, h2, fw)
                return "kamehameha"

        # Check individual hand gestures
        for h in hands:
            if getattr(h, "is_spiderman", False):
                self.draw_spiderman(frame, h, fw)
                primary = "spiderman"
            elif getattr(h, "is_gun", False):
                self.draw_finger_gun(frame, h, fw)
                primary = primary or "finger_gun"
            elif getattr(h, "is_peace", False):
                self.draw_peace_sparkles(frame, h, fw)
                primary = primary or "peace"
            elif getattr(h, "is_repulsor", False):
                self.draw_repulsor(frame, h, fw)
                primary = primary or "repulsor"

        return primary
