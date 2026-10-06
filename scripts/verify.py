# Verify out/final.mp4 against the source: stream properties, frame count, duration,
# audio MD5 (decoded audio must be identical), and build out/contact_sheet.jpg.
import json, subprocess, sys

FF = "./tools/ffmpeg.exe"
PROBE = ["npx", "remotion", "ffprobe"]
SRC = "source/original.mp4"
OUT = "out/final.mp4"


def probe(path):
    r = subprocess.run(PROBE + ["-v", "error", "-count_frames", "-show_entries",
                                "stream=index,codec_type,codec_name,width,height,r_frame_rate,nb_read_frames,duration",
                                "-show_entries", "format=duration", "-of", "json", path],
                       capture_output=True, text=True, shell=True)
    return json.loads(r.stdout)


def md5(path):
    r = subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", path, "-map", "0:a", "-f", "md5", "-"],
                       capture_output=True, text=True)
    return r.stdout.strip()


ok = True
src, out = probe(SRC), probe(OUT)
print("== ffprobe out/final.mp4 ==")
print(json.dumps(out, indent=1))
v = [s for s in out["streams"] if s["codec_type"] == "video"][0]
a = [s for s in out["streams"] if s["codec_type"] == "audio"]
checks = {
    "width 1080": v["width"] == 1080,
    "height 1920": v["height"] == 1920,
    "24 fps": v["r_frame_rate"] == "24/1",
    "4005 frames": int(v["nb_read_frames"]) == 4005,
    "has audio": len(a) == 1,
}
d_src = float(src["format"]["duration"])
d_out = float(out["format"]["duration"])
checks[f"duration within one frame of source ({d_out:.4f} vs {d_src:.4f})"] = abs(d_out - d_src) <= 1 / 24 + 1e-6
m_src, m_out = md5(SRC), md5(OUT)
print("== audio MD5 ==")
print("source:", m_src)
print("final :", m_out)
checks["audio MD5 identical"] = m_src == m_out and m_src != ""
for k, val in checks.items():
    print(("PASS " if val else "FAIL ") + k)
    ok &= val
subprocess.run([sys.executable, "-W", "ignore", "scripts/contact_sheet.py", OUT, "out/contact_sheet.jpg"], check=True)
print("ALL CHECKS PASSED" if ok else "SOME CHECKS FAILED")
sys.exit(0 if ok else 1)
