import sys, subprocess
from faster_whisper import WhisperModel
src = sys.argv[1] if len(sys.argv) > 1 else "work/audio16k.wav"
model_name = sys.argv[2] if len(sys.argv) > 2 else "medium.en"
out = sys.argv[3] if len(sys.argv) > 3 else "work/lyrics_raw.txt"
import numpy as np
raw = subprocess.run(["./tools/ffmpeg.exe", "-v", "error", "-i", src, "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, np.float32).copy()
m = WhisperModel(model_name, device="cpu", compute_type="int8", cpu_threads=12)
segs, info = m.transcribe(audio, beam_size=5, vad_filter=False, word_timestamps=False,
                          condition_on_previous_text=False, no_speech_threshold=0.3)
with open(out, "w", encoding="utf8") as f:
    for s in segs:
        line = f"[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}  (p_nospeech={s.no_speech_prob:.2f})"
        print(line, flush=True); f.write(line + "\n")
