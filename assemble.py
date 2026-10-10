import subprocess
import random
import os
import json

GAMEPLAY_DIR = "assets/gameplay"
MUSIC_DIR = "assets/music"
POSTCARD = "postcard_final.png"
VOICEOVER = "voiceover.mp3"
CAPTIONS = "captions.ass"
OUTPUT = "final.mp4"
POSTCARD_DURATION = 4   # seconds the postcard stays on screen
POSTCARD_WIDTH = 840    # px — scaled down from native size, adjust to taste
MUSIC_VOLUME = 0.07     # low enough to sit under the voice — tune to taste, see notes below

def get_audio_duration(path):
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(json.loads(result.stdout)["format"]["duration"])

def pick_random_file(directory, extensions):
    if not os.path.isdir(directory):
        return None
    files = [f for f in os.listdir(directory) if f.lower().endswith(extensions)]
    if not files:
        return None
    return os.path.join(directory, random.choice(files))

def assemble(output_path=OUTPUT):
    # The headline/story gap is now baked directly into voiceover.mp3 by
    # caption_code.py (real silence generated up front, not spliced in
    # afterward), and captions.ass was built by transcribing that same
    # final file. So both are already correctly aligned - nothing here
    # needs to trim, split, or shift anything.
    total_duration = get_audio_duration(VOICEOVER)

    clip = pick_random_file(GAMEPLAY_DIR, (".mp4", ".mov", ".mkv"))
    if not clip:
        raise FileNotFoundError(f"No clips found in {GAMEPLAY_DIR}")

    music = pick_random_file(MUSIC_DIR, (".mp3", ".wav", ".m4a"))
    print(f"Using clip: {clip} | Music: {music or 'none found - skipping'} | Total duration: {total_duration:.2f}s")

    inputs = [
        "-stream_loop", "-1", "-i", clip,
        "-i", POSTCARD,
        "-i", VOICEOVER,
    ]

    video_chain = (
        "[0:v]scale=w=1080:h=1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1[bg];"
        f"[1:v]scale={POSTCARD_WIDTH}:-1[postcard];"
        f"[bg][postcard]overlay=(W-w)/2:(H-h)/2:enable='between(t,0,{POSTCARD_DURATION})'[withcard];"
        f"[withcard]ass={CAPTIONS}[final]"
    )

    if music:
        inputs += ["-i", music]  # no -stream_loop here — aloop below handles looping
        filter_complex = (
            video_chain + ";"
            f"[3:a]aloop=loop=-1:size=2e9,volume={MUSIC_VOLUME}[music];"
            "[2:a][music]amix=inputs=2:duration=first:dropout_transition=2:normalize=0[aout]"
        )
        audio_map = "[aout]"
    else:
        filter_complex = video_chain
        audio_map = "2:a"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final]", "-map", audio_map,
        "-t", str(total_duration),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"Done: {output_path}")

if __name__ == "__main__":
    assemble()