# out/contact_sheet.jpg: per scene, original frame | our frame | 1:1 hero crop (original | ours)
# out/look/sXX.jpg: 1:1 crops (original left, ours right) of the hero subject and of the ground, for the look checklist
#   python scripts/contact_sheet_v3.py [ours.mp4]
import os, subprocess, sys
import numpy as np, cv2

FF = "./tools/ffmpeg.exe"
OURS = sys.argv[1] if len(sys.argv) > 1 else "out/final.mp4"
# scene: (frame, hero centre, ground centre)
PICK = {1: (146, (540, 1300), (250, 700)), 2: (452, (540, 1100), (250, 600)), 3: (700, (540, 1180), (250, 600)),
        4: (1134, (520, 1200), (600, 1650)), 5: (1500, (560, 1100), (560, 1550)), 6: (1876, (555, 1200), (300, 600)),
        7: (2286, (540, 1150), (300, 1500)), 8: (2570, (540, 1180), (300, 600)), 9: (2814, (540, 1180), (850, 600)),
        10: (3150, (560, 1220), (850, 900)), 11: (3482, (540, 1278), (300, 600)), 12: (3996, (520, 880), (300, 1500))}


def frame(path, f):
    raw = subprocess.run([FF, "-v", "error", "-ss", f"{f/24:.4f}", "-i", path, "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                         capture_output=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(1920, 1080, 3).copy()


def crop(im, c, s=420):
    x = min(max(0, c[0] - s // 2), 1080 - s)
    y = min(max(0, c[1] - s // 2), 1920 - s)
    return im[y:y + s, x:x + s]


def label(im, text):
    cv2.putText(im, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 3, cv2.LINE_AA)
    cv2.putText(im, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return im


def main():
    os.makedirs("out/look", exist_ok=True)
    rows = []
    for s, (f, hero, ground) in PICK.items():
        o, r = frame("source/original.mp4", f), frame(OURS, f)
        h = 420
        w = h * 1080 // 1920
        fo = label(cv2.resize(o, (w, h), interpolation=cv2.INTER_AREA), f"s{s} orig f{f}")
        fr = label(cv2.resize(r, (w, h), interpolation=cv2.INTER_AREA), f"s{s} v3")
        ho = label(crop(o, hero).copy(), "orig 1:1")
        hr = label(crop(r, hero).copy(), "v3 1:1")
        rows.append(np.hstack([fo, fr, ho, hr]))
        look = np.vstack([np.hstack([crop(o, hero, 500), crop(r, hero, 500)]), np.hstack([crop(o, ground, 500), crop(r, ground, 500)])])
        cv2.imwrite(f"out/look/s{s:02d}.jpg", look, [cv2.IMWRITE_JPEG_QUALITY, 92])
    # two columns of scenes to keep the sheet a reasonable shape
    left, right = np.vstack(rows[:6]), np.vstack(rows[6:])
    sheet = np.hstack([left, np.full((left.shape[0], 12, 3), 20, np.uint8), right])
    cv2.imwrite("out/contact_sheet.jpg", sheet, [cv2.IMWRITE_JPEG_QUALITY, 88])
    print("out/contact_sheet.jpg", sheet.shape)


if __name__ == "__main__":
    main()
