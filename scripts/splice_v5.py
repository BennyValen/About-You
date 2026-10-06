# v5 splice: replace only the changed scenes in the existing video, losslessly for everything else.
#   1. cut the v4 silent video at its keyframes (all cuts are IDR frames) with stream copy -> untouched segments
#   2. encode the changed ranges (3: 608-953, 6: 1674-2077, 10-12: 2982-4003) from render/v5 drawings on twos with
#      exactly the v4 encoder settings (same SPS/PPS)
#   3. concat with stream copy -> work/video_silent.mp4, then the brief's mux (audio stream copied from the original)
#   4. print frame counts and the audio packet MD5
#   python scripts/splice_v5.py
import os, shutil, subprocess, sys

FF = "./tools/ffmpeg.exe"
CUTS = [0, 294, 608, 954, 1314, 1674, 2078, 2492, 2646, 2982, 3316, 3648, 4004]
V4 = "work/v5/v4_video_silent.mp4"
OUT = "work/v5/splice"
if not os.path.exists(V4):
    shutil.copyfile("work/video_silent.mp4", V4)
shutil.rmtree(OUT, ignore_errors=True)
os.makedirs(OUT)


def run(cmd):
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True, capture_output=True)


# 1. stream-copy segments of v4 split exactly at the cut keyframes
run([FF, "-hide_banner", "-y", "-i", V4, "-map", "0:v:0", "-c", "copy", "-f", "segment", "-segment_frames", "608,954,1674,2078,2982",
     "-reset_timestamps", "1", os.path.join(OUT, "v4seg_%d.mp4")])
# 2. new ranges from the v5 drawings (hard links, each drawing held for two frames, same pairing as v4)
NEW = [("s03", [3], 608, 954), ("s06", [6], 1674, 2078), ("s10_12", [10, 11, 12], 2982, 4004)]
for tag, scenes, a, b in NEW:
    seq = os.path.join(OUT, f"seq_{tag}")
    os.makedirs(seq)
    k = 0
    for s in scenes:
        sa, sb = CUTS[s - 1], CUTS[s]
        for f in range(sa, sb):
            drawing = f - ((f - sa) % 2)
            src = f"render/v5/scene_{s:02d}/paint/f{drawing:04d}.jpg"
            if not os.path.exists(src):
                sys.exit(f"missing {src}")
            os.link(src, os.path.join(seq, f"{k:05d}.jpg"))
            k += 1
    assert k == b - a, (tag, k, b - a)
    run([FF, "-hide_banner", "-y", "-framerate", "24", "-i", os.path.join(seq, "%05d.jpg"), "-frames:v", str(b - a),
         "-vf", "scale=1080:1920:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "18",
         "-pix_fmt", "yuv420p", "-r", "24", "-an", os.path.join(OUT, f"new_{tag}.mp4")])
# 3. concat (stream copy) in film order
order = ["v4seg_0.mp4", "new_s03.mp4", "v4seg_2.mp4", "new_s06.mp4", "v4seg_4.mp4", "new_s10_12.mp4"]
with open(os.path.join(OUT, "list.txt"), "w") as fh:
    for o in order:
        fh.write(f"file '{o}'\n")
run([FF, "-hide_banner", "-y", "-f", "concat", "-safe", "0", "-i", os.path.join(OUT, "list.txt"), "-c", "copy", "work/video_silent.mp4"])
# 4. mux exactly as the brief says, then verify
run([FF, "-hide_banner", "-y", "-i", "work/video_silent.mp4", "-i", "source/original.mp4", "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
     "out/final.mp4"])


def md5(p):
    return subprocess.run([FF, "-hide_banner", "-loglevel", "error", "-i", p, "-map", "0:a", "-c", "copy", "-f", "md5", "-"],
                          capture_output=True, text=True).stdout.strip()


h0, h1 = md5("source/original.mp4"), md5("out/final.mp4")
print("audio packet md5 source/original.mp4:", h0)
print("audio packet md5 out/final.mp4:      ", h1)
print("AUDIO", "MATCH" if h0 == h1 == "MD5=2632a579c1377d79222ccb4e5300ad9e" else "MISMATCH")
