"""Convert Mooré recordings to WhatsApp voice notes (OGG/Opus, mono) in static/audio/mos/.

Source files must be named after the message they record (intro.m4a, q1.wav, safety.mp3, ...);
any format ffmpeg can read is accepted. Requires ffmpeg on the PATH.

Usage:
    python scripts/convert_audio.py "C:/path/to/recordings"
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.messages import AUDIO_DIR, AUDIO_FILES  # noqa: E402

EXPECTED = sorted(set(AUDIO_FILES.values()))
# WhatsApp shows the play button only for voice notes of 512 KB or less.
MAX_VOICE_NOTE_BYTES = 512 * 1024


def convert(source: Path, target: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(source),
         "-vn", "-ac", "1", "-ar", "48000", "-c:a", "libopus", "-b:a", "32k", str(target)],
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source_dir", type=Path)
    args = parser.parse_args()
    if shutil.which("ffmpeg") is None:
        print("ffmpeg not found on the PATH")
        return 1

    sources = {path.stem.lower(): path for path in args.source_dir.iterdir() if path.is_file()}
    for name in EXPECTED:
        source = sources.get(name)
        if source is None:
            print(f"  missing   {name}")
            continue
        target = AUDIO_DIR / f"{name}.ogg"
        convert(source, target)
        size = target.stat().st_size
        warning = "  (over 512 KB: no play button)" if size > MAX_VOICE_NOTE_BYTES else ""
        print(f"  ok        {name}.ogg  {size // 1024} KB{warning}")
    unknown = sorted(set(sources) - set(EXPECTED))
    if unknown:
        print("  ignored (unexpected names): " + ", ".join(unknown))
    return 0


if __name__ == "__main__":
    sys.exit(main())
