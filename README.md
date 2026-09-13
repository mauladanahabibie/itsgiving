# It's giving...

<table>
  <tr>
    <td><img src="https://github.com/user-attachments/assets/aa5ed48f-70c2-4022-ac7f-87a4c3066a24" width="100%"></td>
    <td><img src="https://github.com/user-attachments/assets/c764c5eb-c17a-47f2-b4b0-49153c8cb3c0" width="100%"></td>
  </tr>
</table>

Pull a face at your webcam. It works out *which* face, and drops the matching
meme over your head, scaled to follow you around the frame. You can extend and
add more memes to your heart's desire.

Point Zoom at its virtual camera and the whole call sees it.

```bash
python its_giving.py              # preview + virtual camera (Meme mode)
python its_giving.py --mode hand  # start directly in Hand FX mode
python its_giving.py --hide       # background mode (preview hidden, full 30 FPS)
python its_giving.py --no-vcam    # preview only
```

**Dual Modes:**
1. **Meme Mode (🎭):** 15 meme reaction face overlays following your head.
2. **Hand FX Mode (🕸️):** Real-time superhero & visual effects on your hands (Spiderman `🤟`, Kamehameha `👐`, Spirit Bomb `🙌`, viral 67 Motion / Hand Sign `6️⃣7️⃣`, Wolverine Claws `✊`, Iron Man repulsor `✋`, Rock On fire `🤘`, Finger Gun `👉`, Doctor Strange Eldritch `☝️`, Peace sparkles `✌️`, Thumbs Up `👍`, and Shaka 6 `🤙`). Press **`m`** at any time to switch instantly!

There's a second file, `its_giving_v2.py`, which is the same thing with the
expression thresholds calibrated to *your* face instead of to a number I
guessed. 

---

## Setup

```bash
python3.12 -m venv venv
source venv/bin/activate           # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Python 3.11 or 3.12. Three MediaPipe models (~15 MB) download themselves on
first run.

**Don't unpin the dependencies.** MediaPipe 0.10.30+ (including 1.0.x) ships
macOS wheels that abort the moment they open a detector, so it's held at
0.10.21. That build needs NumPy 1.x, and OpenCV 5 needs NumPy 2 — and 0.10.21
asks for an *unpinned* `opencv-contrib-python`, which quietly drags OpenCV 5 and
therefore NumPy 2 back in. That's why the OpenCV pins are in there even though
nothing in the code cares. Unpin one and you have to unpin all three.

---

## Running it

```bash
python its_giving_v2.py --calibrate   # once, seven seconds
python its_giving_v2.py               # preview + virtual camera (Meme mode)
python its_giving_v2.py --mode hand   # start in Hand FX mode (Spiderman, etc.)
python its_giving_v2.py --hide        # start hidden in background (full 30 FPS)
```

| key | does |
|---|---|
| `m` | **switch mode** between Meme Reaction (🎭) and Hand FX (🕸️) |
| `q` | quit |
| `d` | toggle the HUD |
| `h` | toggle hide / show preview window |
| `c` | recalibrate (v2) |
| `1`–`9` `0` `-` `=` `[` `p` `s` | force a reaction on screen for 2 seconds (in Meme mode) |

> **Note (Windows 30 FPS Performance):** Minimizing an OpenCV window on Windows can cause the OS to throttle webcam capture down to 10 FPS. When minimized, the app automatically hides the preview window to bypass OS throttling and maintain a solid 30 FPS virtual camera stream in Zoom/Meet. Press `h` at any time to toggle the preview window back on.

---

## Using it in meetings & OBS

The virtual camera stream is published directly by the script using `pyvirtualcam`.

### 1. Prerequisites (Install Driver Once)

| OS | Do this |
|---|---|
| Windows | Install [OBS Studio](https://obsproject.com) (this installs the `OBS Virtual Camera` driver in Windows) |
| macOS | Install [OBS Studio](https://obsproject.com), open it once, then quit it |
| Linux | `sudo apt install v4l2loopback-dkms` then `sudo modprobe v4l2loopback` |

---

### Scenario A: Direct to Zoom, Meet, Teams, or Discord (Recommended)

> **Important:** You do **NOT** need to open the OBS Studio application! OBS only needs to be installed on your computer so its virtual camera driver is registered in Windows.

1. Ensure the OBS Studio application is **closed**.
2. Run the script:
   ```bash
   python its_giving_v2.py
   ```
   It will print:
   ```
   Virtual camera: 'OBS Virtual Camera'  <- pick this camera in Zoom / Meet
   ```
3. Open your meeting app (Zoom, Google Meet, Microsoft Teams, or Discord).
4. Go to **Settings → Video → Camera** and select **`OBS Virtual Camera`**.
5. Your webcam feed with live reactions will now appear directly in your call!

> **Warning (Device Conflict):** Do **NOT** click "Start Virtual Camera" inside the OBS Studio app while the script is running. The Windows virtual camera device only allows **one** application to send video to it at a time. If the script is already broadcasting to `OBS Virtual Camera`, starting it in OBS Studio will fail or crash the camera driver.

---

### Scenario B: Mixing Scenes inside OBS Studio (Streaming / Recording)

If you want to use OBS Studio to manage your stream (e.g. adding overlays, microphones, alerts, or broadcasting to Twitch/YouTube):

1. Run the script with the `--no-vcam` flag (so it doesn't occupy the virtual camera driver):
   ```bash
   python its_giving_v2.py --no-vcam
   ```
2. Open **OBS Studio**.
3. In the **Sources** panel, click **+** and add **Window Capture**.
4. Select the window: `it's giving v2` (or `Reaction Cam`).
5. *(Optional)* You can now safely click **Start Virtual Camera** inside OBS Studio if you want to output your entire mixed OBS scene to Zoom/Meet without any device conflicts!

---

**A few tips:**
- **Start the script before opening Zoom/Meet:** Most meeting apps scan for available camera devices only once at startup.
- **Preview Hidden Mode:** Run with `--hide` or press `h` in the window to keep the virtual camera running at 30 FPS in the background.

---

## The reactions

| pose | do this |
|---|---|
| `time_out` | referee's T — one hand flat on top, one vertical underneath |
| `heart` | two hands, index tips together, thumb tips together |
| `cover_nose` | both hands over your nose and mouth |
| `crashing_out` | both hands to your head, mouth open |
| `dance` | both hands up behind your head, mouth closed |
| `nose_closed` | pinch your nose shut |
| `flirty` | one index fingertip on your lips |
| `tongue_out` | tongue out, mouth open |
| `open_mouth` | jaw drops |
| `disgusted` | scrunch your nose, or brows down and frown |
| `talking_to_wall` | hands in frame, gesturing away |
| `suspicious` | turn your head and squint |
| `spin` | leave the frame entirely |
| `pray` | hands clasped together in prayer in front of chest / chin |
| `speed` | pucker / pout lips facing camera (IShowSpeed rizz) |

Assets live in `assets/`, named after the pose — `heart.jpeg`, `spin.gif`.
Swap in your own by dropping a file with the right name; JPEG, PNG and animated
GIF all work, alpha channels composite properly, and GIF frame timings are read
from the file. A missing asset gets you a red placeholder, not a crash.

---

## Hand FX Mode (Superhero & Action Gestures)

Press **`m`** to switch between **Meme Mode** and **Hand FX Mode** in real-time. In Hand FX mode, facial memes are suppressed and dynamic superhero effects render directly over your hands:

| gesture | hand pose | visual effect |
|---|---|---|
| **Spiderman Web** | `🤟` (Thumb, index, & pinky out; middle & ring folded) | Shoots a procedural web net with radial threads, concentric webbing rings, and a comic **"THWIP!"** badge |
| **Kamehameha / Energy Ball** | `👐` (Both palms open facing each other close together) | Pulsing cyan/white plasma orb with animated electric lightning bolts arcing between palms and a **"KAMEHAMEHA!"** badge |
| **Spirit Bomb / Genkidama** | `🙌` (Both hands open raised high above head & spread) | Massive cosmic blue celestial energy sphere hovering overhead with inflowing universe stardust and a **"GENKIDAMA!"** badge |
| **67 Hand Motion / Sign** | `6️⃣7️⃣` (Both hands open moving alternately up & down in a see-saw motion, OR one hand 6 `🤙` and other hand 7 `👉`) | Animated see-saw balance scale beam with glowing holographic **"6"** and **"7"** hovering over hands and a **"SIX SEVEN (6 7)!"** comic badge |
| **Wolverine Claws** | `✊` (Clenched fist) | Three sharp metallic adamantium blades extending from the knuckles with chrome sheen, sparks, and a comic **"SNIKT!"** badge |
| **Iron Man Repulsor** | `✋` (Single palm flat and open towards camera) | High-tech glowing repulsor core with expanding shockwave energy pulse rings and a **"REPULSOR"** badge |
| **Rock On Fire** | `🤘` (Devil horns: index & pinky out; thumb folded over middle/ring) | Roaring animated flame plumes erupting from fingertips with electric purple lightning and a **"ROCK ON!"** badge |
| **Finger Gun** | `👉` (Index finger pointed forward, thumb up like a pistol hammer) | Glowing laser blaster beam with muzzle flash and a comic **"BANG!"** badge |
| **Doctor Strange Mandala** | `☝️` (Single index finger pointing, thumb & other fingers curled) | Mystic rotating sacred geometry Tao mandala shield with concentric circles, 8-point stars, runes, and sparks with an **"ELDRITCH!"** badge |
| **Peace Sparkles** | `✌️` (Index and middle fingers extended in a V-sign) | Floating orbital magical sparkles, pastel stars, and a **"PEACE!"** badge |
| **Thumbs Up (+1000 Aura)** | `👍` (Only thumb extended upward, fingers curled) | Radiant golden sunburst rays, floating golden celebration stars, and a glowing **"+1000 AURA"** badge |
| **Shaka 6** | `🤙` (Thumb & pinky extended, index/middle/ring curled) | Universal hand sign 6 with electric energy waves and a **"SHAKA 6!"** badge |

---
## Making it yours

### Swapping a meme (~30 seconds)

Drop a file in `assets/` named after the pose — `heart.png` replaces the heart
reaction. JPEG, PNG and animated GIF all work; transparency composites properly
and GIF timings are read from the file. A `something_` prefix is ignored, so
`2019_heart.jpeg` still counts. Press that pose's test key to check it sits
right on your head.

### Adding a pose

**1.** Drop `assets/thinking.png` in place.

**2.** Add the name to `POSES`. The list is checked top to bottom and the first
match wins, so put it above anything it might be mistaken for.

**3.** Add a branch to `decide()`:

```python
    for h in hands:
        if near(h.palm, face.chin, 0.5) and not h.open:
            return "thinking", d
```

You have `face` (`.nose` `.chin` `.mouth` `.w` `.h`, `.b("jawOpen")` for any
blendshape), `hands` (`.palm` `.thumb` `.index`, `.open`), `body`
(`.elbows_up`), `m` for expressions in sigma, and `near(a, b, k)` for "within k
face widths" — which is what keeps it working at any distance from the camera.

**4.** Give it an `ARM` count if it's twitchy, then tune it against the HUD.
Getting it to fire is easy; the work is *stopping* doing it, doing everything
nearby that might be confused with it, and watching the number stay low.

If your pose needs an expression channel that isn't measured yet, add it to `Z`,
`FLOOR` and `measure()`, then put it in `draw_hud()` - you can't tune a number
you can't see.

### Two gotchas

`TEST_KEYS` has one key per pose, matched by position. Adding a fifteenth pose
is fine (it just gets no test key), but removing one without removing a key
crashes when that key is pressed.

If a new pose never fires, check the `POSES` order before you touch any
threshold. Something earlier matching first is the usual cause, and lowering
`Z` can't fix it.

---

## How it works

```
camera frame
     |
 1.  MediaPipe    face: 478 landmarks + 52 blendshapes
                  hands: 2 x 21 points
                  body: shoulders, elbows, wrists
     |
 2.  Measures     face-relative geometry, tongue colour, hand speed
     |
 3.  Baseline     expressions re-expressed in sigma above YOUR neutral face
     |
 4.  decide()     one ordered pass -- first pose that matches wins
     |
 5.  arm / hold   must persist N frames to fire, lingers 10 frames after
     |
  overlay         scaled to your face, alpha-composited, GIFs animated
```

### Normalising away the camera

Landmarks come out as pixel coordinates, which depend on how far you're sitting
from the lens. So nothing is compared in pixels: every distance is divided by
the width of your face box first. `near(hand.index, face.mouth, 0.22)` means
"within 22% of a face width", and that means the same thing at 40 cm and at a
metre and a half. Hand speed gets the same treatment — face-widths per frame.

Head turn is the nose's position between the two edges of your face: 0 facing
the camera, about 0.4 in full profile. Already a ratio, so already scale-free.

### Why fixed thresholds don't work, and what to do instead

This is the interesting part.

MediaPipe's blendshape values are **not zero when your face is at rest**, and
the offset is very personal. Some faces idle at `jawOpen` 0.02; others sit at
0.19 doing nothing. If your mouth naturally turns up you can read `mouthSmile`
0.3 while thinking about absolutely nothing.

So `jawOpen > 0.5` is not one threshold — it's a different threshold for every
face that meets it. Too eager for some, physically unreachable for others. Any
constant you pick is a compromise between people, and no individual user is the
average of those people.

v2 fixes this by measuring your own neutral first. Seven seconds of a bored face
records the **mean and the standard deviation** of all 52 channels, and from
then on every expression is scored as:

```
z = (what the channel reads now - your resting mean) / your resting wobble
```

"6 sigma above your neutral jaw" means the same thing on every face. "Above 0.5"
doesn't. Same two gestures, on a face that idles low and sits still versus one
that idles high and fidgets:

```
                        still face        loose face
resting                 z  +0.1           z  +0.1        both quiet
gasp                    z +38.7           z  +8.7        both fire
nose scrunch            z +19.3           z  +5.5        both fire
```

---

## What's where

```
its_giving_v2.py   the calibrated version — the one to use
its_giving.py      v1: same poses, fixed thresholds
calibration.json   your neutral face (made by --calibrate, gitignored)
requirements.txt   pinned on purpose — read the comments before changing them
assets/            the memes, named after their pose
models/            MediaPipe .task files (downloaded on first run)
```

Inside the file: `POSES` / `Z` / `FLOOR` / `ARM` is the tuning block,
`Baseline` and `run_calibration()` are the seven-second sit-still, `measure()`
turns a face into sigma-above-your-neutral, and `decide()` is the ordered pose
checks.

Want to change **what sets off what**? `decide()`.
Want to change **how easily it goes off**? `Z`, `FLOOR` and `ARM`.
