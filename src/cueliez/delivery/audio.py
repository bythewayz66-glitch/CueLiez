"""Audio cue rendering for professionals.

Generates WAV alert tones (stdlib-only) and TTS-ready cue scripts. Playback is
optional and depends on available system tools.
"""

from __future__ import annotations

import math
import os
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence

from .events import CueEvent, cues_from_observations

_TONE_PROFILES = {
    "low": [(660, 0.10)],
    "medium": [(740, 0.10), (0, 0.04), (740, 0.10)],
    "high": [(880, 0.12), (0, 0.04), (880, 0.12)],
    "critical": [(988, 0.10), (0, 0.03), (1175, 0.10), (0, 0.03), (988, 0.12)],
}


def generate_tone_wav(
    path: str | os.PathLike[str],
    *,
    priority: str = "medium",
    sample_rate: int = 22050,
    volume: float = 0.35,
) -> str:
    """Generate a short WAV alert tone for a cue priority. Uses only stdlib."""
    profile = _TONE_PROFILES.get((priority or "medium").lower(), _TONE_PROFILES["medium"])
    frames = bytearray()
    amplitude = max(0.0, min(1.0, float(volume))) * 32767
    for freq, duration in profile:
        n = int(sample_rate * duration)
        for i in range(n):
            if freq <= 0:
                sample = 0
            else:
                t = i / sample_rate
                # simple envelope to reduce clicks
                env = 1.0
                edge = min(200, n // 4)
                if i < edge:
                    env = i / max(1, edge)
                elif i > n - edge:
                    env = (n - i) / max(1, edge)
                sample = int(amplitude * env * math.sin(2 * math.pi * freq * t))
            frames.extend(struct.pack("<h", sample))
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(frames))
    return str(out)


def _player_command(path: str) -> Optional[List[str]]:
    for name, args in (("paplay", [path]), ("aplay", ["-q", path]), ("ffplay", ["-nodisp", "-autoexit", "-loglevel", "error", path])):
        exe = shutil.which(name)
        if exe:
            return [exe] + args
    return None


class AudioCueRenderer:
    """Render audio cue assets and playback attempts."""

    def __init__(self, *, output_dir: str | os.PathLike[str] = "cueliez_audio_cues", allow_playback: bool = False):
        self.output_dir = Path(output_dir)
        self.allow_playback = allow_playback

    def render_assets(self, cues: Sequence[CueEvent]) -> Dict[str, Any]:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        assets = []
        for c in cues:
            wav = generate_tone_wav(self.output_dir / f"{c.cue_id}.wav", priority=c.priority)
            script_path = self.output_dir / f"{c.cue_id}.txt"
            script_path.write_text(c.audio_script + "\n", encoding="utf-8")
            assets.append({
                "cue_id": c.cue_id,
                "priority": c.priority,
                "tone_wav": wav,
                "script_text": str(script_path),
                "audio_script": c.audio_script,
            })
        manifest = {
            "type": "cueliez_audio_cues",
            "cue_count": len(cues),
            "assets": assets,
            "notice": "Audio cues are observation prompts for professional review; not findings.",
        }
        (self.output_dir / "manifest.json").write_bytes(
            __import__("json").dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")
        )
        return manifest

    def play_tone(self, path: str | os.PathLike[str]) -> Dict[str, Any]:
        cmd = _player_command(str(path))
        if not cmd:
            return {"played": False, "reason": "no_audio_player_available", "path": str(path)}
        if not self.allow_playback:
            return {"played": False, "reason": "playback_disabled", "path": str(path), "command": cmd}
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, check=False)
            return {"played": proc.returncode == 0, "returncode": proc.returncode, "path": str(path), "command": cmd,
                    "stderr": (proc.stderr or "")[:300]}
        except Exception as e:
            return {"played": False, "reason": "playback_error", "error": str(e), "path": str(path)}

    def render_panel(self, observations: Sequence[Mapping[str, Any]], **kwargs: Any) -> Dict[str, Any]:
        cues = cues_from_observations(observations, **{k: v for k, v in kwargs.items() if k in ("min_score", "max_cues")})
        return self.render_assets(cues)
