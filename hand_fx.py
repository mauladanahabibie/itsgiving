"""
hand_fx.py — Real-time superhero & hand gesture effects for itsgiving.

Supported Gestures & Effects:
  1. Spiderman (🤟): Dynamic spiderweb shooting from wrist with concentric web arcs & "THWIP!" badge.
  2. Kamehameha / Energy Ball (👐): Glowing plasma sphere with animated electric lightning between palms.
  3. Spirit Bomb / Genkidama (🙌): Massive cosmic blue celestial sphere gathered above head with energy streaks.
  4. 67 Hand Sign & Motion (6 7): Viral 67 see-saw weighing options motion with giant glowing holographic "6" & "7", beam scale, and "SIX SEVEN!" badge.
  5. Wolverine Claws (✊): Sharp adamantium metal blades extending from clenched knuckles with "SNIKT!" badge.
  6. Iron Man Repulsor (✋): High-tech glowing repulsor core with shockwave pulse on open palm.
  7. Rock On / Fire Horns (🤘): Roaring fire flame plumes rising from fingers and electric arc with "ROCK ON!" badge.
  8. Finger Gun (👉): Blaster laser beam & muzzle flash with "BANG!" comic text.
  9. Doctor Strange Eldritch Mandala (☝️): Rotating mystic sacred geometry Tao mandala shield with runes & sparks.
 10. Peace Sign (✌️): Floating animated sparkles, pastel bubbles & stars with "PEACE!" badge.
 11. Thumbs Up / +1000 Aura (👍): Radiant golden sunburst rays, floating celebration stars, and "+1000 AURA" badge.
 12. Shaka Six (🤙): Universal hand sign 6 with glowing electric wave and "SHAKA 6" badge.
"""
import math
import random
import time
import cv2
import numpy as np


def draw_glow_circle(overlay, center, radius, color, thickness=-1):
    """Draw a circle on an overlay for alpha blending."""
    cv2.circle(overlay, (int(center[0]), int(center[1])), max(1, int(radius)), color, thickness, cv2.LINE_AA)


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
        px, py = -uy, ux

        ox, oy = wrist[0], wrist[1]
        base_reach = max(fw * 2.2, 180.0)

        angles = [-0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6]
        endpoints = []
        for a in angles:
            cos_a, sin_a = math.cos(a), math.sin(a)
            rx = ux * cos_a - uy * sin_a
            ry = ux * sin_a + uy * cos_a
            reach = base_reach * (1.0 + 0.15 * math.cos(self.frame_count * 0.3 + a))
            tx = np.clip(ox + rx * reach, 0, W - 1)
            ty = np.clip(oy + ry * reach, 0, H - 1)
            endpoints.append((tx, ty))

        overlay = frame.copy()
        for ep in endpoints:
            cv2.line(overlay, (int(ox), int(oy)), (int(ep[0]), int(ep[1])), (255, 255, 255), 2, cv2.LINE_AA)

        for r_step in [0.25, 0.50, 0.75, 1.0]:
            arc_pts = []
            for ep in endpoints:
                ax = ox + (ep[0] - ox) * r_step
                ay = oy + (ep[1] - oy) * r_step
                arc_pts.append([int(ax), int(ay)])
            if len(arc_pts) > 1:
                cv2.polylines(overlay, [np.array(arc_pts, np.int32)], False, (240, 240, 255), 2, cv2.LINE_AA)

        cv2.circle(overlay, (int(ox), int(oy)), int(fw * 0.25), (255, 255, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, (int(ox), int(oy)), int(fw * 0.35), (0, 0, 255), 3, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        badge_x = int(np.clip(ox + px * fw * 0.9, 30, W - 140))
        badge_y = int(np.clip(oy + py * fw * 0.9, 40, H - 30))
        draw_comic_badge(frame, "THWIP!", (badge_x, badge_y), bg_color=(30, 30, 220), text_color=(255, 255, 255), scale=0.9)

    def draw_kamehameha(self, frame, hand_a, hand_b, fw):
        """Render glowing plasma energy orb with lightning bolts between two open palms (👐)."""
        H, W = frame.shape[:2]
        center = ((hand_a.palm + hand_b.palm) / 2)
        cx, cy = int(center[0]), int(center[1])

        pulse = 1.0 + 0.12 * math.sin(self.frame_count * 0.4)
        r = int(fw * 0.65 * pulse)

        overlay = frame.copy()
        draw_glow_circle(overlay, (cx, cy), r * 1.6, (255, 150, 0), -1)   # Cyan outer aura
        draw_glow_circle(overlay, (cx, cy), r * 1.1, (255, 240, 80), -1)  # Electric cyan-white
        draw_glow_circle(overlay, (cx, cy), r * 0.55, (255, 255, 255), -1) # Blinding core

        for _ in range(3):
            angle = random.uniform(0, 2 * math.pi)
            arc_len = random.uniform(r * 0.8, r * 1.5)
            pts = [(cx, cy)]
            for step in range(1, 4):
                frac = step / 3.0
                curr_dist = arc_len * frac
                curr_ang = angle + random.uniform(-0.35, 0.35)
                lx = int(cx + math.cos(curr_ang) * curr_dist)
                ly = int(cy + math.sin(curr_ang) * curr_dist)
                pts.append((lx, ly))
            for i in range(len(pts) - 1):
                cv2.line(overlay, pts[i], pts[i + 1], (255, 255, 200), 2, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        draw_comic_badge(frame, "KAMEHAMEHA!", (cx - 85, cy - r - 25), bg_color=(230, 80, 0), text_color=(255, 255, 255), scale=0.85)

    def draw_spirit_bomb(self, frame, h1, h2, face, fw):
        """Render Dragon Ball Genkidama / Spirit Bomb (🙌) cosmic gathering sphere."""
        H, W = frame.shape[:2]
        cx = int((h1.palm[0] + h2.palm[0]) / 2)
        cy = int(min(h1.palm[1], h2.palm[1]) - fw * 0.75)
        cy = max(cy, int(fw * 0.7))

        pulse = 1.0 + 0.07 * math.sin(self.frame_count * 0.35)
        R = int(fw * 1.15 * pulse)

        overlay = frame.copy()
        draw_glow_circle(overlay, (cx, cy), int(R * 1.5), (255, 120, 0), -1)
        draw_glow_circle(overlay, (cx, cy), int(R * 1.15), (255, 220, 50), -1)
        draw_glow_circle(overlay, (cx, cy), int(R * 0.75), (255, 255, 180), -1)
        draw_glow_circle(overlay, (cx, cy), int(R * 0.40), (255, 255, 255), -1)

        for i in range(8):
            ang = self.frame_count * 0.04 + i * (2 * math.pi / 8)
            t = (self.frame_count * 0.05 + i * 0.25) % 1.0
            dist_start = max(W, H) * 0.65
            dist_curr = dist_start * (1.0 - t) + R * t
            ex = int(cx + math.cos(ang) * dist_curr)
            ey = int(cy + math.sin(ang) * dist_curr)
            tail_x = int(cx + math.cos(ang) * (dist_curr + fw * 0.4))
            tail_y = int(cy + math.sin(ang) * (dist_curr + fw * 0.4))
            if 0 <= ex < W and 0 <= ey < H:
                cv2.line(overlay, (tail_x, tail_y), (ex, ey), (255, 240, 100), 2, cv2.LINE_AA)
                cv2.circle(overlay, (ex, ey), 3, (255, 255, 255), -1, cv2.LINE_AA)

        for palm in [h1.palm, h2.palm]:
            px, py = int(palm[0]), int(palm[1])
            pts = [(px, py)]
            for s in range(1, 5):
                alpha = s / 5.0
                lx = int(px + (cx - px) * alpha + random.uniform(-15, 15))
                ly = int(py + (cy - py) * alpha + random.uniform(-15, 15))
                pts.append((lx, ly))
            pts.append((cx, cy))
            for j in range(len(pts) - 1):
                cv2.line(overlay, pts[j], pts[j + 1], (255, 220, 100), 3, cv2.LINE_AA)
                cv2.line(overlay, pts[j], pts[j + 1], (255, 255, 255), 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        draw_comic_badge(frame, "GENKIDAMA!", (cx - 75, cy - int(R * 1.15) - 20),
                         bg_color=(200, 90, 0), text_color=(255, 255, 255), scale=0.95)

    def draw_six_seven(self, frame, h1, h2, fw):
        """Render viral 67 Hand Motion & Hand Sign (see-saw weighing options motion with glowing 6 & 7)."""
        H, W = frame.shape[:2]
        if h1.palm[0] < h2.palm[0]:
            left_h, right_h = h1, h2
        else:
            left_h, right_h = h2, h1

        lx, ly = int(left_h.palm[0]), int(left_h.palm[1])
        rx, ry = int(right_h.palm[0]), int(right_h.palm[1])

        overlay = frame.copy()

        # Seesaw balance beam connecting both hands
        cv2.line(overlay, (lx, ly), (rx, ry), (0, 200, 255), 4, cv2.LINE_AA)
        cv2.line(overlay, (lx, ly), (rx, ry), (255, 255, 255), 2, cv2.LINE_AA)

        # Fulcrum balance point
        mid_x, mid_y = int((lx + rx) / 2), int((ly + ry) / 2)
        cv2.circle(overlay, (mid_x, mid_y), 10, (0, 140, 255), -1, cv2.LINE_AA)
        cv2.circle(overlay, (mid_x, mid_y), 5, (255, 255, 255), -1, cv2.LINE_AA)

        # Pulsing energy aura under each hand
        pulse_6 = 1.0 + 0.15 * math.sin(self.frame_count * 0.4)
        pulse_7 = 1.0 + 0.15 * math.cos(self.frame_count * 0.4)
        draw_glow_circle(overlay, (lx, ly), int(fw * 0.4 * pulse_6), (0, 140, 255), -1)
        draw_glow_circle(overlay, (rx, ry), int(fw * 0.4 * pulse_7), (255, 180, 0), -1)

        # Floating numbers 6 and 7 particles
        for i in range(4):
            dx = math.sin(self.frame_count * 0.1 + i * 1.5) * fw * 0.3
            dy_6 = (self.frame_count * 3 + i * 20) % int(fw * 0.8)
            dy_7 = (self.frame_count * 3 + (i + 2) * 20) % int(fw * 0.8)
            p6_x, p6_y = int(lx + dx), int(ly - fw * 0.4 - dy_6)
            p7_x, p7_y = int(rx + dx), int(ry - fw * 0.4 - dy_7)
            if 0 <= p6_x < W and 0 <= p6_y < H:
                cv2.putText(overlay, "6", (p6_x, p6_y), cv2.FONT_HERSHEY_DUPLEX, 0.6, (0, 220, 255), 2, cv2.LINE_AA)
            if 0 <= p7_x < W and 0 <= p7_y < H:
                cv2.putText(overlay, "7", (p7_x, p7_y), cv2.FONT_HERSHEY_DUPLEX, 0.6, (255, 240, 0), 2, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        # Giant Holographic '6' above Left Hand
        g6_x, g6_y = int(lx - 25), int(ly - fw * 0.45)
        cv2.putText(frame, "6", (g6_x, g6_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 0, 0), 8, cv2.LINE_AA)
        cv2.putText(frame, "6", (g6_x, g6_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 140, 255), 4, cv2.LINE_AA)
        cv2.putText(frame, "6", (g6_x, g6_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Giant Holographic '7' above Right Hand
        g7_x, g7_y = int(rx - 25), int(ry - fw * 0.45)
        cv2.putText(frame, "7", (g7_x, g7_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (0, 0, 0), 8, cv2.LINE_AA)
        cv2.putText(frame, "7", (g7_x, g7_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (255, 180, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, "7", (g7_x, g7_y), cv2.FONT_HERSHEY_TRIPLEX, 2.6, (255, 255, 255), 2, cv2.LINE_AA)

        # Central Comic Action Badge
        badge_y = int(min(ly, ry) - fw * 0.85)
        badge_y = max(badge_y, 40)
        draw_comic_badge(frame, "SIX SEVEN (6 7)!", (mid_x - 110, badge_y),
                         bg_color=(220, 30, 80), text_color=(255, 255, 0), scale=0.9)

    def draw_shaka_six(self, frame, hand, fw):
        """Render Shaka / Six (🤙) hand sign with neon 6 badge and electric waves."""
        H, W = frame.shape[:2]
        cx, cy = int(hand.palm[0]), int(hand.palm[1])
        t_tip, p_tip = hand.thumb, hand.pinky

        overlay = frame.copy()
        x1, y1 = int(t_tip[0]), int(t_tip[1])
        x2, y2 = int(p_tip[0]), int(p_tip[1])
        cv2.line(overlay, (x1, y1), (x2, y2), (0, 255, 200), 3, cv2.LINE_AA)
        cv2.line(overlay, (x1, y1), (x2, y2), (255, 255, 255), 1, cv2.LINE_AA)

        draw_glow_circle(overlay, (x1, y1), int(fw * 0.2), (0, 220, 255), -1)
        draw_glow_circle(overlay, (x2, y2), int(fw * 0.2), (0, 220, 255), -1)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)

        hx, hy = int(cx - 20), int(cy - fw * 0.45)
        cv2.putText(frame, "6", (hx, hy), cv2.FONT_HERSHEY_TRIPLEX, 2.2, (0, 0, 0), 7, cv2.LINE_AA)
        cv2.putText(frame, "6", (hx, hy), cv2.FONT_HERSHEY_TRIPLEX, 2.2, (0, 230, 255), 3, cv2.LINE_AA)
        cv2.putText(frame, "6", (hx, hy), cv2.FONT_HERSHEY_TRIPLEX, 2.2, (255, 255, 255), 1, cv2.LINE_AA)

        draw_comic_badge(frame, "SHAKA 6!", (cx - 50, cy - int(fw * 0.75)),
                         bg_color=(0, 160, 220), text_color=(255, 255, 255), scale=0.8)

    def draw_wolverine_claws(self, frame, hand, fw):
        """Render Wolverine adamantium claws (✊) with metallic blades and sparks."""
        H, W = frame.shape[:2]
        wrist = hand.wrist
        knuckle_mid = hand.pts[9]
        dx, dy = knuckle_mid[0] - wrist[0], knuckle_mid[1] - wrist[1]
        length = max(np.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length
        px, py = -uy, ux

        claw_len = max(fw * 1.5, 140.0)
        knuckle_pairs = [
            (hand.pts[5] + hand.pts[9]) / 2,    # between index and middle
            (hand.pts[9] + hand.pts[13]) / 2,   # between middle and ring
            (hand.pts[13] + hand.pts[17]) / 2,  # between ring and pinky
        ]

        overlay = frame.copy()
        for i, base_pt in enumerate(knuckle_pairs):
            bx, by = float(base_pt[0]), float(base_pt[1])
            fan = (i - 1) * 0.08
            c_ux = ux * math.cos(fan) - uy * math.sin(fan)
            c_uy = ux * math.sin(fan) + uy * math.cos(fan)
            c_px, c_py = -c_uy, c_ux

            tip_x = bx + c_ux * claw_len
            tip_y = by + c_uy * claw_len

            w_base = 5.0
            p1 = (int(bx - c_px * w_base), int(by - c_py * w_base))
            p2 = (int(bx + c_px * w_base), int(by + c_py * w_base))
            p3 = (int(tip_x), int(tip_y))
            poly = np.array([p1, p2, p3], np.int32)

            cv2.fillPoly(overlay, [poly], (70, 75, 85))
            cv2.polylines(overlay, [poly], True, (40, 45, 50), 2, cv2.LINE_AA)

            p1_in = (int(bx - c_px * (w_base - 1.5)), int(by - c_py * (w_base - 1.5)))
            p2_in = (int(bx + c_px * (w_base - 1.5)), int(by + c_py * (w_base - 1.5)))
            poly_in = np.array([p1_in, p2_in, p3], np.int32)
            cv2.fillPoly(overlay, [poly_in], (215, 225, 235))

            cv2.line(overlay, (int(bx), int(by)), (int(tip_x), int(tip_y)), (255, 255, 255), 2, cv2.LINE_AA)

            for _ in range(2):
                sx = int(bx + random.uniform(-10, 10))
                sy = int(by + random.uniform(-10, 10))
                if 0 <= sx < W and 0 <= sy < H:
                    cv2.circle(overlay, (sx, sy), random.randint(2, 4), (0, 215, 255), -1, cv2.LINE_AA)
                    cv2.circle(overlay, (sx, sy), 1, (255, 255, 255), -1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

        mid_knuckle = knuckle_pairs[1]
        bx = int(mid_knuckle[0] + px * fw * 0.7)
        by = int(mid_knuckle[1] + py * fw * 0.7)
        draw_comic_badge(frame, "SNIKT!", (bx - 30, by), bg_color=(20, 20, 200), text_color=(0, 255, 255), scale=0.85)

    def draw_thumbs_up(self, frame, hand, fw):
        """Render Thumbs Up (👍) golden radiant aura, rising celebration stars, and +1000 AURA badge."""
        H, W = frame.shape[:2]
        tip = hand.thumb
        tx, ty = int(tip[0]), int(tip[1])

        overlay = frame.copy()
        r = int(fw * 0.35)
        draw_glow_circle(overlay, (tx, ty), r * 1.5, (0, 180, 255), -1)
        draw_glow_circle(overlay, (tx, ty), r * 0.9, (0, 230, 255), -1)
        draw_glow_circle(overlay, (tx, ty), r * 0.4, (255, 255, 255), -1)

        num_rays = 8
        ray_len = fw * 0.75
        base_angle = self.frame_count * 0.05
        for i in range(num_rays):
            ang = base_angle + i * (2 * math.pi / num_rays)
            rx = int(tx + math.cos(ang) * ray_len)
            ry = int(ty + math.sin(ang) * ray_len)
            cv2.line(overlay, (tx, ty), (rx, ry), (0, 230, 255), 2, cv2.LINE_AA)

        for i in range(5):
            sx = int(tx + math.sin(self.frame_count * 0.1 + i * 1.4) * fw * 0.6)
            sy = int(ty - ((self.frame_count * 3 + i * 25) % int(fw * 1.4)))
            if 0 <= sx < W and 0 <= sy < H:
                s_size = int(5 + 2 * math.sin(self.frame_count * 0.2 + i))
                cv2.circle(overlay, (sx, sy), s_size, (0, 240, 255), -1, cv2.LINE_AA)
                cv2.circle(overlay, (sx, sy), max(1, s_size // 2), (255, 255, 255), -1, cv2.LINE_AA)
                cv2.line(overlay, (sx - s_size, sy), (sx + s_size, sy), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(overlay, (sx, sy - s_size), (sx, sy + s_size), (255, 255, 255), 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        draw_comic_badge(frame, "+1000 AURA", (tx - 65, ty - int(fw * 0.55)),
                         bg_color=(0, 160, 255), text_color=(255, 255, 255), scale=0.8)

    def draw_rock_on_fire(self, frame, hand, fw):
        """Render Rock On (🤘) heavy metal fire flames and electric arc."""
        H, W = frame.shape[:2]
        t1, t2 = hand.index, hand.pinky
        tips = [t1, t2]

        overlay = frame.copy()
        for tip in tips:
            tx, ty = int(tip[0]), int(tip[1])
            for f in range(6):
                drift = math.sin(self.frame_count * 0.25 + f * 1.3) * (fw * 0.12)
                fy = ty - int((self.frame_count * 4 + f * 12) % int(fw * 0.9))
                fx = int(tx + drift)
                fr = int(max(4, (fw * 0.22) * (1.0 - (ty - fy) / max(fw * 0.9, 1.0))))
                cv2.circle(overlay, (fx, fy), fr, (0, 0, 230), -1, cv2.LINE_AA)
                cv2.circle(overlay, (fx, fy), int(fr * 0.7), (0, 140, 255), -1, cv2.LINE_AA)
                cv2.circle(overlay, (fx, fy), int(fr * 0.35), (100, 255, 255), -1, cv2.LINE_AA)

        x1, y1 = int(t1[0]), int(t1[1])
        x2, y2 = int(t2[0]), int(t2[1])
        pts = [(x1, y1)]
        segs = 6
        for s in range(1, segs):
            t = s / segs
            lx = int(x1 + (x2 - x1) * t + random.uniform(-10, 10))
            ly = int(y1 + (y2 - y1) * t + random.uniform(-10, 10))
            pts.append((lx, ly))
        pts.append((x2, y2))
        for j in range(len(pts) - 1):
            cv2.line(overlay, pts[j], pts[j + 1], (255, 100, 255), 3, cv2.LINE_AA)
            cv2.line(overlay, pts[j], pts[j + 1], (255, 255, 255), 1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        cx = int((t1[0] + t2[0]) / 2)
        cy = int(min(t1[1], t2[1]) - fw * 0.6)
        draw_comic_badge(frame, "ROCK ON!", (cx - 55, cy), bg_color=(0, 40, 230), text_color=(0, 255, 255), scale=0.85)

    def draw_doctor_strange(self, frame, hand, fw):
        """Render Doctor Strange Eldritch Tao Mandala (☝️) sacred geometry shield."""
        H, W = frame.shape[:2]
        tip = hand.index
        cx, cy = int(tip[0]), int(tip[1])

        overlay = frame.copy()
        mandala_r = int(fw * 0.65)
        rot = self.frame_count * 0.04

        cv2.circle(overlay, (cx, cy), mandala_r, (0, 140, 255), 2, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), int(mandala_r * 0.72), (0, 200, 255), 2, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), int(mandala_r * 0.40), (0, 230, 255), 2, cv2.LINE_AA)
        cv2.circle(overlay, (cx, cy), int(mandala_r * 0.15), (255, 255, 255), -1, cv2.LINE_AA)

        for offset in [0.0, math.pi / 4]:
            star_pts = []
            for k in range(4):
                a = rot + offset + k * (math.pi / 2)
                px = int(cx + math.cos(a) * mandala_r * 0.72)
                py = int(cy + math.sin(a) * mandala_r * 0.72)
                star_pts.append([px, py])
            cv2.polylines(overlay, [np.array(star_pts, np.int32)], True, (0, 220, 255), 2, cv2.LINE_AA)

        for i in range(16):
            a = -rot * 0.8 + i * (2 * math.pi / 16)
            p_in = (int(cx + math.cos(a) * (mandala_r - 6)), int(cy + math.sin(a) * (mandala_r - 6)))
            p_out = (int(cx + math.cos(a) * (mandala_r + 6)), int(cy + math.sin(a) * (mandala_r + 6)))
            cv2.line(overlay, p_in, p_out, (0, 210, 255), 2, cv2.LINE_AA)

        for s in range(8):
            a = rot * 2.0 + s * (2 * math.pi / 8)
            sp_r = mandala_r * (0.5 + 0.5 * ((self.frame_count * 0.05 + s * 0.2) % 1.0))
            sx = int(cx + math.cos(a) * sp_r)
            sy = int(cy + math.sin(a) * sp_r)
            if 0 <= sx < W and 0 <= sy < H:
                cv2.circle(overlay, (sx, sy), 3, (0, 180, 255), -1, cv2.LINE_AA)
                cv2.circle(overlay, (sx, sy), 1, (255, 255, 255), -1, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.70, frame, 0.30, 0, frame)
        draw_comic_badge(frame, "ELDRITCH!", (cx - 55, cy - mandala_r - 18),
                         bg_color=(0, 110, 230), text_color=(255, 255, 255), scale=0.8)

    def draw_repulsor(self, frame, hand, fw):
        """Render Iron Man Repulsor (✋) with glowing reactor core & shockwaves."""
        H, W = frame.shape[:2]
        cx, cy = int(hand.palm[0]), int(hand.palm[1])

        pulse = 1.0 + 0.15 * math.sin(self.frame_count * 0.5)
        r = int(fw * 0.35 * pulse)

        overlay = frame.copy()
        draw_glow_circle(overlay, (cx, cy), r * 1.8, (255, 180, 0), -1)
        draw_glow_circle(overlay, (cx, cy), r * 1.2, (255, 255, 120), -1)
        draw_glow_circle(overlay, (cx, cy), r * 0.6, (255, 255, 255), -1)

        wave_r = int((r * 1.5 + (self.frame_count * 4) % (r * 2)))
        cv2.circle(overlay, (cx, cy), wave_r, (255, 255, 200), 3, cv2.LINE_AA)

        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        draw_comic_badge(frame, "REPULSOR", (cx - 60, cy - r - 25), bg_color=(0, 140, 255), text_color=(255, 255, 255), scale=0.7)

    def draw_finger_gun(self, frame, hand, fw):
        """Render Finger Gun laser beam & muzzle flash (👉) with BANG! badge."""
        H, W = frame.shape[:2]
        tip = hand.index
        base = hand.pts[6]
        dx, dy = tip[0] - base[0], tip[1] - base[1]
        length = max(np.hypot(dx, dy), 1.0)
        ux, uy = dx / length, dy / length

        reach = max(W, H) * 1.2
        target_x = int(tip[0] + ux * reach)
        target_y = int(tip[1] + uy * reach)

        overlay = frame.copy()
        cv2.line(overlay, (int(tip[0]), int(tip[1])), (target_x, target_y), (0, 0, 255), 8, cv2.LINE_AA)
        cv2.line(overlay, (int(tip[0]), int(tip[1])), (target_x, target_y), (150, 255, 255), 3, cv2.LINE_AA)

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
                cv2.line(frame, (sx - star_size * 2, sy), (sx + star_size * 2, sy), (255, 255, 255), 1, cv2.LINE_AA)
                cv2.line(frame, (sx, sy - star_size * 2), (sx, sy + star_size * 2), (255, 255, 255), 1, cv2.LINE_AA)

        draw_comic_badge(frame, "PEACE!", (int(cx - 35), int(cy - fw * 0.5)),
                         bg_color=(200, 60, 220), text_color=(255, 255, 255), scale=0.7)

    def render(self, frame, hands, face):
        """Main rendering entrypoint. Returns name of primary gesture detected, or None."""
        self.update()
        fw = face.w if face is not None else 120.0
        H, W = frame.shape[:2]
        primary = None

        # Check two-hand gestures first
        if len(hands) >= 2:
            h1, h2 = hands[0], hands[1]
            hand_dist = float(np.hypot(h1.palm[0] - h2.palm[0], h1.palm[1] - h2.palm[1]))
            face_top = face.nose[1] if face is not None else H * 0.45

            # 1. Spirit Bomb / Genkidama (hands open, raised high up, spread)
            if h1.open and h2.open and h1.palm[1] < face_top and h2.palm[1] < face_top and hand_dist >= 1.2 * fw:
                self.draw_spirit_bomb(frame, h1, h2, face, fw)
                return "spirit_bomb"

            # 2. Kamehameha (hands open, close together in front at similar height)
            if h1.open and h2.open and hand_dist < 2.0 * fw and abs(h1.palm[1] - h2.palm[1]) < 0.25 * fw:
                self.draw_kamehameha(frame, h1, h2, fw)
                return "kamehameha"

            # 3. 67 Hand Motion / Sign (Seesaw weighing options motion OR 6 🤙 + 7 👉)
            is_67_sign = (getattr(h1, "is_six", False) and (getattr(h2, "is_gun", False) or getattr(h2, "is_pointing", False))) or \
                         (getattr(h2, "is_six", False) and (getattr(h1, "is_gun", False) or getattr(h1, "is_pointing", False)))
            is_67_seesaw = (h1.open and h2.open and (h1.palm[1] >= face_top or h2.palm[1] >= face_top) and
                            abs(h1.palm[1] - h2.palm[1]) > 0.20 * fw and hand_dist < 4.5 * fw)

            if is_67_sign or is_67_seesaw:
                self.draw_six_seven(frame, h1, h2, fw)
                return "six_seven"

        # Check individual hand gestures
        for h in hands:
            if getattr(h, "is_spiderman", False):
                self.draw_spiderman(frame, h, fw)
                primary = "spiderman"
            elif getattr(h, "is_fist", False):
                self.draw_wolverine_claws(frame, h, fw)
                primary = primary or "wolverine"
            elif getattr(h, "is_six", False):
                self.draw_shaka_six(frame, h, fw)
                primary = primary or "shaka_six"
            elif getattr(h, "is_thumbs_up", False):
                self.draw_thumbs_up(frame, h, fw)
                primary = primary or "thumbs_up"
            elif getattr(h, "is_rock_on", False):
                self.draw_rock_on_fire(frame, h, fw)
                primary = primary or "rock_on"
            elif getattr(h, "is_pointing", False):
                self.draw_doctor_strange(frame, h, fw)
                primary = primary or "doctor_strange"
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
