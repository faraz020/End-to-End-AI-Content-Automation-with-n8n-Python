import asyncio
import sys
import os
import json
import subprocess
from faster_whisper import WhisperModel
import edge_tts

VOICE = "en-IE-ConnorNeural"  # try en-GB-RyanNeural or en-US-EricNeural too — pick one and keep it consistent, it becomes your channel's "voice"
STORY_GAP = 0.7              # seconds of silence between the headline and the story.
                            # MUST match STORY_GAP in assemble.py if assemble.py still
                            # references it anywhere (the simplified version below doesn't).
VOICEOVER_OUT = "voiceover.mp3"
CAPTIONS_OUT = "captions.ass"
SAMPLE_RATE = 24000         # edge-tts neural voices output 24kHz mono — matches the
                             # generated silence so ffmpeg doesn't need to guess/convert

async def synthesize(text, out_path):
    communicate = edge_tts.Communicate(text, VOICE, rate="+44%")  # faster pacing for retention
    await communicate.save(out_path)

def concat_with_gap(part1_path, part2_path, gap_seconds, out_path):
    """
    Joins two audio clips with an exact gap_seconds of real silence baked
    directly between them at generation time. Because we control the gap
    up front, there's no ambiguity for assemble.py to resolve later - the
    headline/story boundary IS the boundary, by construction.
    """
    filter_complex = (
        f"[0:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=mono[a0];"
        f"[1:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=mono[a1];"
        f"[2:a]aformat=sample_rates={SAMPLE_RATE}:channel_layouts=mono[a2];"
        "[a0][a1][a2]concat=n=3:v=0:a=1[out]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", part1_path,
        "-f", "lavfi", "-t", str(gap_seconds), "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono",
        "-i", part2_path,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        out_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)

def format_ass_time(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h}:{m:02d}:{s:05.2f}"

def build_ass(words, out_path=CAPTIONS_OUT, words_per_group=1):
    header = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial Black,115,&H0000FFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,0,0,1,12,0,2,60,60,700,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [header]
    for i in range(0, len(words), words_per_group):
        group = words[i:i + words_per_group]
        start = format_ass_time(group[0].start)
        end = format_ass_time(group[-1].end)
        text = " ".join(w.word.strip() for w in group)
        lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")
    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

def transcribe(audio_path=VOICEOVER_OUT):
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    words = []
    for seg in segments:
        words.extend(seg.words)
    return words

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Raw text passed directly - no headline/story split to work with,
        # so this falls back to the old single-pass behaviour with no gap.
        story_text = sys.argv[1]
        asyncio.run(synthesize(story_text, VOICEOVER_OUT))
    elif os.path.exists("story_output.json"):
        with open("story_output.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        headline_part = "headline_part.mp3"
        story_part = "story_part.mp3"
        asyncio.run(synthesize(data["headline"], headline_part))
        asyncio.run(synthesize(data["story"], story_part))
        concat_with_gap(headline_part, story_part, STORY_GAP, VOICEOVER_OUT)
        os.remove(headline_part)
        os.remove(story_part)
    else:
        story_text = "This is a test story for caption generation."
        asyncio.run(synthesize(story_text, VOICEOVER_OUT))

    words = transcribe()
    build_ass(words)
    print(f"Done: {VOICEOVER_OUT} + {CAPTIONS_OUT} ({len(words)} words)")