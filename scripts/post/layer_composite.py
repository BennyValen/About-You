# v5 "replace only the changed layers" for scenes 10 and 11: the new painted drawing is used inside a feathered mask of
# the edited elements (walker / birds, their shadows, the thread and its shadow, plants the walker touches); everywhere
# else the approved v4 painted drawing is kept, so nothing outside the edits changes. (The paint pass draws strokes with
# a data-dependent random order, so a fresh paint of an unchanged area differs by 1-2 levels; this keeps it exact.)
#   python scripts/post/layer_composite.py 10 11
import json, os, shutil, sys
import numpy as np, cv2

R4, R5 = "render/v4", "render/v5"
W, H = 1080, 1920


def hero(root, s, f, dil):
    h = cv2.imread(f"{root}/scene_{s:02d}/aux/hero_{f:04d}.png", 0)
    if h is None:
        return np.zeros((H, W), np.uint8)
    h = cv2.resize(h, (W, H))
    return cv2.dilate((h > 40).astype(np.uint8), np.ones((dil, dil), np.uint8))


def red(x):
    x = x.astype(np.int16)
    return ((x[..., 2] > 140) & (x[..., 1] < 100) & (x[..., 0] < 100) & (x[..., 2] > x[..., 1] + 90)).astype(np.uint8)


def mask_for(s, f, a, b, extra):
    m = hero(R4, s, f, 45) | hero(R5, s, f, 45)
    m |= cv2.dilate(red(a) | red(b), np.ones((31, 31), np.uint8))
    if s == 10:
        x, y = [int(v) for v in extra[f]["hat"]]
        cv2.circle(m, (x, y), 200, 1, -1)                         # walker, the sunflowers that part around it
        cv2.rectangle(m, (x - 200, y), (x + 120, H), 1, -1)       # its long shadow down the frame
    if s == 11:
        hb = hero(R4, s, f, 45) | hero(R5, s, f, 45)
        for k in (20, 40, 60, 80, 110, 140, 200, 260):            # bird shadows on the clouds (down-right)
            M_ = np.float32([[1, 0, 0.77 * k], [0, 1, 0.64 * k]])
            m |= cv2.warpAffine(hb, M_, (W, H))
    return m


def run(s):
    d5 = f"{R5}/scene_{s:02d}"
    raw = f"{d5}/paint_raw"
    if not os.path.isdir(raw):
        shutil.move(f"{d5}/paint", raw)
        os.makedirs(f"{d5}/paint")
    extra = {r["f"]: r for r in json.load(open(f"{d5}/walk_log.json"))} if s == 10 else {}
    masks = {}
    for p in sorted(os.listdir(raw)):
        f = int(p[1:5])
        a = cv2.imread(f"{R4}/scene_{s:02d}/paint/{p}")
        b = cv2.imread(f"{raw}/{p}")
        m = mask_for(s, f, a, b, extra).astype(np.float32)
        al = cv2.GaussianBlur(m, (0, 0), 8)[..., None]
        al = np.clip(al * 1.5, 0, 1)                                # fully new inside, 8 px feather outside
        out = (b.astype(np.float32) * al + a.astype(np.float32) * (1 - al) + 0.5).astype(np.uint8)
        cv2.imwrite(f"{d5}/paint/{p}", out, [cv2.IMWRITE_JPEG_QUALITY, 100, cv2.IMWRITE_JPEG_SAMPLING_FACTOR, cv2.IMWRITE_JPEG_SAMPLING_FACTOR_444])
        cv2.imwrite(f"{d5}/aux/editmask_{f:04d}.png", (np.clip(al[..., 0], 0, 1) * 255).astype(np.uint8))
    print(f"scene {s}: composited {len(os.listdir(raw))} drawings (new inside the edit mask, v4 outside)")


if __name__ == "__main__":
    for s in [int(x) for x in sys.argv[1:]]:
        run(s)
