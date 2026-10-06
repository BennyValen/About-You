# Story notes

Sources: full-resolution frames 3840–4002 at 4 per second (`work/ref_end_full/`, sheet `work/compare/end_sheet.jpg`), the scene 12 track (`scripts/analysis_s12.py`, output `work/s12_track.json`), the red-pixel scan of the whole film (`scripts/analysis_redscan.py`), and 1:1 crops (`work/scene_notes/crops/s12.jpg`).

## Verdict

Your reading is correct, and I'm continuing without stopping. One traveler (A) crosses 12 landscapes, always trailing a red thread down to the bottom edge of the frame. In the last shot a second traveler (B) walks in from the top edge with their own red thread trailing up to the top edge. The two walk toward each other and end a few steps apart, still moving. Two people on red threads ("the red thread of fate") crossing the world to meet.

One correction to your mode-of-travel list, from looking at the frames: scene 4 is **skating on a frozen lake** (white coat, skate blades, scratch marks in the ice), not swimming. Scene 5 is **riding a camel**. Scene 11 is A **flying among a V of white cranes**; A is the lead bird's rider/position. The thread hangs from the lead crane, and no separate human is visible.

## The two people (scene 12)

| | A (the traveler) | B (arrives at the end) |
|---|---|---|
| Body | Slim adult, seen from straight above, about 60–70 px across the shoulders at 1080 wide. | Same build and scale as A. |
| Hair | Dark brown/black, short, top of head visible. | Dark, slightly longer, falls behind the head. |
| Clothing | **Navy/indigo long-sleeve top** (#3e4c96 range) and slate-blue trousers, dark shoes. | **Pale/white top** (reads off-white/very light grey) and dark trousers. |
| Gait | Walking briskly up the frame. Arms swing, and the right arm is often raised/forward (camera side). | Walking down the frame toward A. |
| Shadow | Long, soft violet shadow to the **lower-left** (sun upper-right, low), about 3–4 body lengths. | Same direction and length. |
| Thread attach | **Waist/hip, back**: the thread leaves A's lower back and runs down to the bottom edge. | **Waist/hip, back**: the thread leaves B's lower back and runs up to the top edge. |

## Frame by frame (scene 12, frames 3648–4003)

- **3648–3930** (152.0–163.75 s): A walks up at a fixed screen position, about (403, 1297) at full res. The camera follows, accelerating from 8.4 to about 13.5 px/frame (measured on moving sandbar features; phase correlation is fooled by the screen-fixed glare). A's thread runs from A's back almost straight down, swaying gently and dragging on the wet flat, slightly to A's left (x about 400 → 430 at the bottom edge). No other red is in frame. The top edge is clean from 3648 to 3930.
- **~3930** (163.75 s): B's head appears at the **top edge, x ≈ 718**. B's thread is already behind B, touching the top edge (first red at the top edge: frame 3934).
- **3930–3960** (163.75–165.0 s): B walks down and slightly left (x 718 → 686 → about 650) at about 20 px/frame in screen space. That is B's own walk plus the still-moving camera. B's thread trails up and right to the top edge (top end x ≈ 740–790). A keeps walking.
- **3940–3965** (164.2–165.2 s): the camera decelerates (8.1 → 3.5 → 0.8 px/frame) and stops at about frame 3966.
- **3966–4003** (165.25–166.83 s): the **camera is still**, and **both people keep walking**. A moves up the frame from about (440, 1170) to about (500, 1000), and B down from about (630, 600) to about (575, 850). They face each other. In the final frame the gap is about 150–180 px (a couple of body lengths): a few steps apart, still moving. Both shadows go lower-left. A's thread still runs from A's back down to the bottom edge, now longer and more slanted (bottom end about x 270–330). B's thread runs from B's back up and right to the top edge (about x 800).
- **At no time** is there a thread between A and B, a third thread, or a thread appearing from nothing. Each thread is one continuous curve from its owner to its frame edge.
- **No fade:** mean brightness is constant to the last frame (RGB ≈ 189/158/167).

## Earlier signs of B?

The red-pixel scan flagged a few short runs of frames before 163 s with reddish pixels at the top edge: 332–335, 420–457 and 562 (scene 2), 1412 and 1630–1673 (scene 5), 2340–2461 (scene 7). I viewed the top 260 px of each (`work/compare/topedge.png`). They are the **rust-red ballast strip beside the track** (scene 2), **orange-pink sand striations** (scene 5) and **rust-orange lichen** (scene 7). None of them is a thread or a figure. **The first real sign of B is frame ~3930 (163.75 s).** Confirmed.

## Lyrics vs scenes

Transcription: `work/lyrics.txt` (demucs vocal stem → faster-whisper medium; soft breathy vocal, words approximate).

| Time (s) | Lyric (approx.) | Scene on screen | Fit |
|---|---|---|---|
| 0–49 | (instrumental; brief vocal swells ~10.5, 16, 24, 44 s) | 1 night train, 2 contour forest, 3 lily pads, 4 frozen lake | journey begins |
| 49.7–55 | "No place…" | 4 frozen lake (skater) | |
| 55–61 | "Somewhere I go / when I need to remember / your face" | 5 desert (camel), from 54.75 s | longing, searching |
| 61–70 | "We get married / in our house" | 5 desert | imagined future together |
| 70–80 | "…when we try to recall / how we met" | 6 lagoon sailboat (from 69.75 s) | memory |
| 80–102 | "Do you think I have forgotten? (×3) … about you" | 6 lagoon → 7 paraglider (from 86.6 s) | "I haven't forgotten you" |
| 102–166 | wordless humming / "ooh" | 7 canyon, 8 night swim, 9 cyclist, 10 sunflowers, 11 cranes, 12 tidal flats | music carries the reunion |
| 161.8–163 | last vocal phrase | 12, just before B enters (163.75 s) | B appears right after the last sung phrase |

Mood: tender, nostalgic, a love song about remembering someone and finding your way back to them. It fits two people bound by red threads walking toward each other. Timing in the build comes only from the video, never from the lyrics.
