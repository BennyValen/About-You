import numpy as np, cv2, sys
fr = np.load("work/gray540.npy")
def flow_dy(n, k=6, mask_center=True):
    a = cv2.GaussianBlur(fr[n], (0, 0), 1.2); b = cv2.GaussianBlur(fr[n + k], (0, 0), 1.2)
    f = cv2.calcOpticalFlowFarneback(a, b, None, 0.5, 4, 25, 4, 7, 1.5, 0)
    mag = np.hypot(f[..., 0], f[..., 1])
    g = cv2.Sobel(a, cv2.CV_32F, 1, 0) ** 2 + cv2.Sobel(a, cv2.CV_32F, 0, 1) ** 2
    m = g > np.percentile(g, 60)          # only textured pixels
    if mask_center:
        m[380:820, 120:420] = False        # exclude the subject region (540x960 coords)
    return float(np.median(f[..., 1][m])) * 2 / k, float(np.median(f[..., 0][m])) * 2 / k
for a, b in [(3316, 3647), (3648, 4003), (2492, 2645)]:
    print("range", a, b)
    for n in range(a + 2, b - 8, 24):
        dy, dx = flow_dy(n)
        print(f"  f{n} t={n/24:6.2f}s dy {dy:6.2f} dx {dx:6.2f} px/f")
