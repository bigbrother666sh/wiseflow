import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT / "crews/main/skills/native-ui-card"
WRAPPER = SKILL / "native-ui-card.sh"


class CardRenderTest(unittest.TestCase):
    def render(self, spec, root, name):
        inp = root / f"{name}.json"
        out = root / name
        inp.write_text(json.dumps(spec, ensure_ascii=False))
        result = subprocess.run(["bash", str(WRAPPER), "--input", str(inp), "--output", str(out)], capture_output=True, text=True)
        return result, out

    def test_both_forms_render_complete_assets(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            group = json.loads((SKILL / "examples/group.json").read_text())
            external = SKILL / "assets/avatars/square/avatar-03.jpg"
            group["group"]["before"][0]["avatar"] = str(external)
            group["avatar_sources"] = {str(external): "test licensed asset"}
            result, out = self.render(group, root, "group")
            self.assertEqual(result.returncode, 0, result.stderr)
            with Image.open(out / "page-01.png") as image:
                self.assertEqual(image.size, (2160, 2880))
            self.assertIn("test licensed asset", (out / "assets-manifest.json").read_text())
            self.assertNotIn("file:///home/", (out / "page-01.html").read_text())
            self.assertNotIn("情景演绎", (out / "page-01.html").read_text())

            qa = json.loads((SKILL / "examples/qa.json").read_text())
            qa["qa"]["stats"] = {"关注": "286", "回答": "19", "浏览": "1.3万"}
            result, out = self.render(qa, root, "qa")
            self.assertEqual(result.returncode, 0, result.stderr)
            for page in ("page-01", "page-02", "page-03"):
                with Image.open(out / f"{page}.png") as image:
                    self.assertEqual(image.size, (2160, 2880))
            self.assertIn("sub-reply", (out / "page-02.html").read_text())
            self.assertIn("关注 <b>286</b>", (out / "page-01.html").read_text())
            self.assertNotIn("情景演绎", "".join((out / f"page-0{page}.html").read_text() for page in (1, 2, 3)))

    def test_overflow_stops_before_image(self):
        with tempfile.TemporaryDirectory() as scratch:
            root = Path(scratch)
            group = json.loads((SKILL / "examples/group.json").read_text())
            group["group"]["point"] = "先给常看的书留一个顺手的位置。" * 160
            group["group"]["highlight"] = "先给常看的书留一个顺手的位置。"
            result, out = self.render(group, root, "overflow")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("版面溢出", result.stderr)
            self.assertFalse((out / "page-01.png").exists())


if __name__ == "__main__":
    unittest.main()
