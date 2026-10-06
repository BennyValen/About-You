# Multilingual transcription of the separated vocals (read-only analysis; output stays in work/).
import subprocess, numpy as np
from faster_whisper import WhisperModel
raw = subprocess.run(["./tools/ffmpeg.exe", "-v", "error", "-i", "work/sep/vocals.wav", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"], capture_output=True).stdout
audio = np.frombuffer(raw, np.float32).copy()
m = WhisperModel("medium", device="cpu", compute_type="int8", cpu_threads=12)
lang, prob, all_probs = m.detect_language(audio[16000 * 53:16000 * 83])
print("detected language:", lang, round(prob, 3), sorted(all_probs, key=lambda x: -x[1])[:5], flush=True)
with open("work/lyrics_ml.txt", "w", encoding="utf8") as f:
    for task in ("transcribe", "translate"):
        segs, info = m.transcribe(audio, task=task, beam_size=5, vad_filter=True,
                                  vad_parameters=dict(min_silence_duration_ms=400, threshold=0.35),
                                  condition_on_previous_text=False, no_speech_threshold=0.5)
        f.write(f"## {task} (language {info.language} p={info.language_probability:.2f})\n")
        for s in segs:
            line = f"[{s.start:7.2f} - {s.end:7.2f}] {s.text.strip()}"
            print(task, line, flush=True); f.write(line + "\n")
