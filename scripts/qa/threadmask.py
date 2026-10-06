# Thin red line detector shared by the analysis and the thread QA gate.
import numpy as np, cv2
def thread_mask(rgb, scale=1.0):
    f = rgb.astype(np.float32)
    red = f[..., 0] - np.maximum(f[..., 1], f[..., 2])
    k = max(3, int(round(9 * scale)) | 1)
    local = cv2.GaussianBlur(red, (k, k), 0)
    m = ((red - local) > 14) & (red > 38) & (f[..., 0] > 110)
    return m


def render_thread_mask(rgb, scale=1.0):
    """stricter detector for our renders: the cord is a saturated red (#d22a2b family)"""
    f = rgb.astype(np.float32)
    sat = f[..., 0] - np.maximum(f[..., 1], f[..., 2])
    # crimson cord: green and blue roughly equal (orange rust / lichen have G >> B and are excluded)
    return (sat > 75) & (f[..., 0] > 140) & (f[..., 1] < 120) & ((f[..., 1] - f[..., 2]) < 25)


def render_thread_mask_hyst(rgb, scale=1.0):
    """hysteresis: strong cord pixels plus weaker (edge-blurred / vignetted) red pixels connected to them"""
    f = rgb.astype(np.float32)
    sat = f[..., 0] - np.maximum(f[..., 1], f[..., 2])
    strong = render_thread_mask(rgb, scale).astype(np.uint8)
    h = rgb.shape[0]
    band = np.zeros(sat.shape, bool)
    band[: int(0.12 * h)] = True
    band[int(0.88 * h):] = True
    weak = (((sat > 38) | (band & (sat > 26))) & (f[..., 0] > 110) & ((f[..., 1] - f[..., 2]) < 22)).astype(np.uint8)
    n, lab = cv2.connectedComponents(np.maximum(weak, strong), connectivity=8)
    keep = np.unique(lab[strong > 0])
    keep = keep[keep > 0]
    return np.isin(lab, keep)
