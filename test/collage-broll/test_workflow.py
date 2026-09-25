"""Collage B-roll must keep the expert-video baseline stages and silent output."""

import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
WRAPPER = ROOT / "crews/content-producer/skills/expert-video/tools/video-producer/video-producer.sh"


def run(*args):
    return subprocess.run([str(WRAPPER), *map(str, args)], text=True, capture_output=True)


class CollageWorkflowTests(unittest.TestCase):
    def test_full_stage_chain_and_verified_silent_delivery(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "brief.md").write_text("# 纸拼贴测试\n- workflow：collage-broll\n", encoding="utf-8")
            for command in ("script-write", "script-self-eval"):
                result = run(command, project)
                self.assertEqual(result.returncode, 0, result.stderr)
            stages = (
                ("storyboard-build", "storyboard/storyboard.json"),
                ("shot-decompose", "storyboard/shot_decompose.json"),
                ("character-register", "characters/registry.json"),
                ("slot-plan", "slots/slot-plan.json"),
                ("asset-resolve", "slots/asset-resolve.json"),
                ("slideshow-risk", "slots/slideshow-risk.json"),
                ("delivery-promise-lock", "slots/delivery-promise.json"),
                ("render-shot", "render/collage-render-plan.json"),
            )
            for number, (command, artifact) in enumerate(stages, 3):
                result = run(command, project)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"[done] Stage {number} collage-broll", result.stdout)
                self.assertEqual(json.loads((project / artifact).read_text())["stage"], number)

            result = run("mix-audio", project)
            self.assertEqual(result.returncode, 0, result.stderr)
            plan_path = project / "audio/collage-audio-plan.json"
            plan = json.loads(plan_path.read_text())
            self.assertEqual(plan["stage"], 11)

            clip = project / "render/item-01/final.mp4"
            clip.parent.mkdir(parents=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                            "color=c=blue:s=160x288:r=12:d=1", "-c:v", "libx264", "-threads", "1",
                            str(clip)], check=True)
            manifest = project / "render/item-01/segments.json"
            manifest.write_text(json.dumps([{"name": "item-01", "path": "render/item-01/final.mp4"}]))
            unconfirmed = run("assemble", project, "--manifest", manifest, "--verify-fps", 12)
            self.assertNotEqual(unconfirmed.returncode, 0)
            self.assertIn("sound_policy 尚未核定", unconfirmed.stderr + unconfirmed.stdout)
            plan["sound_policy"] = "silent"
            plan_path.write_text(json.dumps(plan))
            result = run("assemble", project, "--manifest", manifest, "--verify-fps", 12)
            self.assertEqual(result.returncode, 0, result.stderr)
            video = project / "video.mp4"
            self.assertEqual(video.read_bytes(), clip.read_bytes())

            result = run("motion-audit", project)
            self.assertEqual(result.returncode, 0, result.stderr)
            audit = json.loads((project / "review/collage-motion-audit.json").read_text())
            self.assertEqual(audit["workflow"], "collage-broll")
            self.assertIn("layers", audit)

            output = project / "video_normalized.mp4"
            result = run("normalize", video, "--output", output, "--silent-ok")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_bytes(), video.read_bytes())
            report = json.loads(output.with_suffix(".normalization.json").read_text())
            self.assertEqual(report["reason"], "verified_silent_video")

    def test_missing_previous_stage_fails_instead_of_skipping(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "brief.md").write_text("- workflow：collage-broll\n")
            result = run("shot-decompose", project)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Stage 4 前置缺失", result.stderr + result.stdout)
            self.assertFalse((project / "storyboard/shot_decompose.json").exists())


if __name__ == "__main__":
    unittest.main()
