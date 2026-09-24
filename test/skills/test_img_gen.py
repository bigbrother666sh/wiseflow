#!/usr/bin/env python3
"""Unit tests for gen.py (阿里云百炼图像生成/编辑，双模式).

Covers:
- 模式解析：WORKSPACE_ID+MODELSTUDIO_API_KEY → 业务空间；否则 AWK_API_KEY → agent plan
- 端点常量：业务空间 maas.aliyuncs.com / agent plan token-plan
- 模型候选链：qwen-image-3.0-pro 链 / wan2.7-image-pro 链
- size 校验（总像素 [512², 2048²]，宽高比 [1/8, 8]，规范化为 W*H，auto 放行）
- Payload 构造（text-to-image vs image-edit，content 顺序 image 在前 text 在后）
- 本地图转 data URI
- API request shape（Bearer token、multimodal-generation 端点）
- 响应解析 output.choices[*].message.content[*].image
- 候选链 fallback 判定（403/404 直接 fallback；400 仅模型类错误 fallback）

All HTTP calls are mocked — these are unit tests.
"""
import base64
import argparse
import io
import tempfile
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / 'skills/awk-img-gen/scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import gen  # noqa: E402


def _env(**overrides):
    """构造受控 env dict（清空所有相关变量后按需注入）。"""
    base = {
        k: v for k, v in os.environ.items()
        if k not in ("WORKSPACE_ID", "MODELSTUDIO_API_KEY", "DASHSCOPE_API_KEY", "AWK_API_KEY", "AWK_GEN_KEY", "ARK_API_KEY")
    }
    base.update({k: v for k, v in overrides.items() if v is not None})
    return base


class TestConstants(unittest.TestCase):
    def test_agent_plan_base(self):
        self.assertEqual(gen.AGENT_PLAN_BASE, "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1")

    def test_ws_base_template(self):
        self.assertEqual(
            gen.WS_BASE_TEMPLATE.format(wsid="llm-abc"),
            "https://llm-abc.cn-beijing.maas.aliyuncs.com/api/v1",
        )

    def test_gen_path(self):
        self.assertEqual(gen.GEN_PATH, "/services/aigc/multimodal-generation/generation")

    def test_model_chains(self):
        self.assertEqual(gen.WS_MODEL_CHAIN[0], "qwen-image-3.0-pro")
        self.assertIn("qwen-image-3.0", gen.WS_MODEL_CHAIN)
        self.assertIn("qwen-image-2.0-pro-2026-06-22", gen.WS_MODEL_CHAIN)
        self.assertEqual(gen.PLAN_MODEL_CHAIN[0], "wan2.7-image-pro")
        self.assertIn("wan2.7-image", gen.PLAN_MODEL_CHAIN)

    def test_size_constraints_match_bailian_docs(self):
        self.assertEqual(gen.MIN_TOTAL_PIXELS, 512 * 512)
        self.assertEqual(gen.MAX_TOTAL_PIXELS, 2048 * 2048)
        self.assertEqual(gen.MIN_ASPECT_RATIO, 1 / 8)
        self.assertEqual(gen.MAX_ASPECT_RATIO, 8)


class TestResolveMode(unittest.TestCase):
    def test_workspace_mode_preferred(self):
        with mock.patch.dict(os.environ, _env(
            WORKSPACE_ID="llm-abc", MODELSTUDIO_API_KEY="sk-ws", AWK_API_KEY="sk-sp-x"
        ), clear=True):
            base, key, chain, mode = gen.resolve_mode()
        self.assertEqual(mode, "workspace")
        self.assertEqual(base, "https://llm-abc.cn-beijing.maas.aliyuncs.com/api/v1")
        self.assertEqual(key, "sk-ws")
        self.assertEqual(chain, gen.WS_MODEL_CHAIN)

    def test_workspace_dashscope_key_alias(self):
        with mock.patch.dict(os.environ, _env(
            WORKSPACE_ID="llm-abc", DASHSCOPE_API_KEY="sk-ds"
        ), clear=True):
            base, key, chain, mode = gen.resolve_mode()
        self.assertEqual(mode, "workspace")
        self.assertEqual(key, "sk-ds")

    def test_agent_plan_when_no_workspace(self):
        with mock.patch.dict(os.environ, _env(AWK_API_KEY="sk-sp-x"), clear=True):
            base, key, chain, mode = gen.resolve_mode()
        self.assertEqual(mode, "agent-plan")
        self.assertEqual(base, gen.AGENT_PLAN_BASE)
        self.assertEqual(chain, gen.PLAN_MODEL_CHAIN)

    def test_workspace_id_without_key_falls_to_agent_plan(self):
        with mock.patch.dict(os.environ, _env(
            WORKSPACE_ID="llm-abc", AWK_API_KEY="sk-sp-x"
        ), clear=True):
            _base, _key, _chain, mode = gen.resolve_mode()
        self.assertEqual(mode, "agent-plan")

    def test_no_credentials_exits_1(self):
        with mock.patch.dict(os.environ, _env(), clear=True):
            with self.assertRaises(SystemExit) as ctx:
                gen.resolve_mode()
        self.assertEqual(ctx.exception.code, 1)


class TestSizeNormalization(unittest.TestCase):
    def test_presets_accepted_and_normalized(self):
        for size in ("2048x2048", "2688x1536", "1536x2688", "2368x1728", "1728x2368"):
            self.assertEqual(gen.normalize_size(size), size.replace("x", "*"))

    def test_star_separator_accepted(self):
        self.assertEqual(gen.normalize_size("2048*2048"), "2048*2048")

    def test_chinese_x_accepted(self):
        self.assertEqual(gen.normalize_size("2048×2048"), "2048*2048")

    def test_auto_passthrough(self):
        self.assertEqual(gen.normalize_size("auto"), "auto")
        self.assertEqual(gen.normalize_size("AUTO"), "auto")

    def test_total_pixels_below_min_rejected(self):
        # 500x500 = 250000 < 262144
        with self.assertRaises(SystemExit):
            gen.normalize_size("500x500")

    def test_total_pixels_above_max_rejected(self):
        # 2848x1600 = 4556800 > 4194304（旧火山 2K 预设，百炼超限）
        with self.assertRaises(SystemExit):
            gen.normalize_size("2848x1600")

    def test_aspect_ratio_out_of_range_rejected(self):
        # 4096x400: ratio 10.24 > 8（面积 1638400 合法但比例超限）
        with self.assertRaises(SystemExit):
            gen.normalize_size("4096x400")

    def test_invalid_format_rejected(self):
        for bad in ("abc", "1024", "1024x", "x1024", "", "2K", "4K"):
            with self.assertRaises(SystemExit):
                gen.normalize_size(bad)


class TestResolveImageRef(unittest.TestCase):
    def test_url_passthrough(self):
        self.assertEqual(gen.resolve_image_ref("https://a.com/x.jpg"), "https://a.com/x.jpg")

    def test_data_uri_passthrough(self):
        ref = "data:image/png;base64,AAAA"
        self.assertEqual(gen.resolve_image_ref(ref), ref)

    def test_local_file_to_data_uri(self):
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\nfakebytes")
            tmp = f.name
        try:
            ref = gen.resolve_image_ref(tmp)
            self.assertTrue(ref.startswith("data:image/png;base64,"))
            self.assertEqual(base64.b64decode(ref.split(",", 1)[1]), b"\x89PNG\r\n\x1a\nfakebytes")
        finally:
            os.unlink(tmp)

    def test_missing_file_exits_1(self):
        with self.assertRaises(SystemExit):
            gen.resolve_image_ref("/nonexistent/x.jpg")


class TestPayloadConstruction(unittest.TestCase):
    def _args(self, **overrides):
        defaults = dict(
            prompt="a cat", model=None, image=None, image2=None, image3=None,
            image_size=None, seed=None, watermark=False, prompt_extend=False,
        )
        defaults.update(overrides)
        return mock.Mock(**defaults)

    def test_text_to_image_default(self):
        payload = gen.build_payload(self._args(), "qwen-image-3.0-pro")
        self.assertEqual(payload["model"], "qwen-image-3.0-pro")
        msgs = payload["input"]["messages"]
        self.assertEqual(len(msgs), 1)
        self.assertEqual(msgs[0]["role"], "user")
        # 文生图 content 只有一个 text 项
        self.assertEqual(msgs[0]["content"], [{"text": "a cat"}])
        self.assertEqual(payload["parameters"]["size"], "2048*2048")
        self.assertFalse(payload["parameters"]["watermark"])
        self.assertFalse(payload["parameters"]["prompt_extend"])

    def test_explicit_size_normalized(self):
        payload = gen.build_payload(self._args(image_size="1536x2688"), "m")
        self.assertEqual(payload["parameters"]["size"], "1536*2688")

    def test_image_edit_content_order(self):
        # 编辑模式：image 项在前，text 在后（百炼文档要求）
        payload = gen.build_payload(
            self._args(image="https://a.com/x.jpg", image2="https://a.com/y.jpg"), "m"
        )
        content = payload["input"]["messages"][0]["content"]
        self.assertEqual(content[0], {"image": "https://a.com/x.jpg"})
        self.assertEqual(content[1], {"image": "https://a.com/y.jpg"})
        self.assertEqual(content[2], {"text": "a cat"})
        # 编辑模式缺省不带 size
        self.assertNotIn("size", payload["parameters"])

    def test_image_edit_explicit_size_included(self):
        payload = gen.build_payload(
            self._args(image="https://a.com/x.jpg", image_size="2048x2048"), "m"
        )
        self.assertEqual(payload["parameters"]["size"], "2048*2048")

    def test_seed_and_flags(self):
        payload = gen.build_payload(self._args(seed=42, watermark=True, prompt_extend=True), "m")
        self.assertEqual(payload["parameters"]["seed"], 42)
        self.assertTrue(payload["parameters"]["watermark"])
        self.assertTrue(payload["parameters"]["prompt_extend"])


class TestApiRequest(unittest.TestCase):
    @mock.patch("gen.urllib.request.urlopen")
    def test_request_shape(self, mock_urlopen):
        mock_urlopen.return_value.__enter__.return_value.read.return_value = json.dumps({
            "output": {"choices": [{"message": {"content": [{"image": "https://x/a.png"}]}}]},
        }).encode("utf-8")
        url = f"{gen.AGENT_PLAN_BASE}{gen.GEN_PATH}"
        resp = gen.api_request(url, {"model": "m"}, "sk-sp-test")
        args, _ = mock_urlopen.call_args
        req = args[0]
        self.assertEqual(req.headers["Authorization"], "Bearer sk-sp-test")
        self.assertEqual(req.headers["Content-type"], "application/json")
        self.assertEqual(req.full_url, url)
        self.assertEqual(gen.extract_image_urls(resp), ["https://x/a.png"])

    @mock.patch("gen.urllib.request.urlopen")
    def test_http_error_raises_with_body(self, mock_urlopen):
        import urllib.error
        from io import BytesIO
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://x/api", code=404, msg="Not Found", hdrs=None, fp=BytesIO(b'{"code":"ModelNotFound"}'),
        )
        with self.assertRaises(gen.ImgGenHTTPError) as ctx:
            gen.api_request("https://x/api", {}, "k")
        self.assertEqual(ctx.exception.code, 404)


class TestExtractImageUrls(unittest.TestCase):
    def test_multi_choices_multi_content(self):
        resp = {"output": {"choices": [
            {"message": {"content": [{"image": "https://x/a.png"}, {"text": "ignored"}]}},
            {"message": {"content": [{"image": "https://x/b.png"}]}},
        ]}}
        self.assertEqual(gen.extract_image_urls(resp), ["https://x/a.png", "https://x/b.png"])

    def test_empty_output(self):
        self.assertEqual(gen.extract_image_urls({}), [])
        self.assertEqual(gen.extract_image_urls({"output": {}}), [])


class TestModelUnavailable(unittest.TestCase):
    def test_403_404_always(self):
        self.assertTrue(gen.is_model_unavailable(gen.ImgGenHTTPError(403, "")))
        self.assertTrue(gen.is_model_unavailable(gen.ImgGenHTTPError(404, "")))

    def test_400_model_hints_only(self):
        self.assertTrue(gen.is_model_unavailable(gen.ImgGenHTTPError(400, '{"code":"ModelNotFound"}')))
        self.assertTrue(gen.is_model_unavailable(gen.ImgGenHTTPError(400, "model not found: x")))
        self.assertFalse(gen.is_model_unavailable(gen.ImgGenHTTPError(400, '{"code":"InvalidParameter","message":"size invalid"}')))

    def test_5xx_not_model_unavailable(self):
        self.assertFalse(gen.is_model_unavailable(gen.ImgGenHTTPError(500, "")))
        self.assertFalse(gen.is_model_unavailable(gen.ImgGenHTTPError(429, "")))


class TestIntegrationDryRun(unittest.TestCase):
    """Subprocess-level smoke tests."""

    def test_help_runs_without_env(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "gen.py"), "--help"],
            capture_output=True, text=True, timeout=10, check=False,
            env=_env(),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("image", result.stdout.lower())

    def test_missing_credentials_exits_1(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "gen.py"), "--prompt", "x"],
            capture_output=True, text=True, timeout=10, check=False,
            env=_env(),
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("AWK_API_KEY", result.stderr)
        self.assertIn("WORKSPACE_ID", result.stderr)


class TestVolc(unittest.TestCase):
    def args(self, **changes):
        values = dict(prompt="test", image=None, image2=None, image3=None,
                      image_size=None, seed=None, watermark=False, prompt_extend=False)
        values.update(changes)
        return argparse.Namespace(**values)

    def test_priority_and_override(self):
        with mock.patch.dict(os.environ, _env(AWK_GEN_KEY="volc-key", WORKSPACE_ID="ws",
                            MODELSTUDIO_API_KEY="ws-key", AWK_API_KEY="plan-key"), clear=True):
            self.assertEqual(gen.resolve_mode()[1:], ("volc-key", gen.VOLC_MODEL_CHAIN, "volc"))
            self.assertEqual(gen.resolve_mode("dashscope")[3], "workspace")
            self.assertEqual(gen.resolve_mode("volcengine")[3], "volc")

    def test_no_wrong_key_or_cross_platform_fallback(self):
        with mock.patch.dict(os.environ, _env(ARK_API_KEY="llm-key", AWK_API_KEY="plan"), clear=True):
            with self.assertRaises(SystemExit):
                gen.resolve_mode("volc")
            self.assertEqual(gen.resolve_mode()[3], "agent-plan")
        with mock.patch.dict(os.environ, _env(AWK_GEN_KEY="volc"), clear=True):
            with self.assertRaises(SystemExit):
                gen.resolve_mode("dashscope")

    def test_sizes(self):
        for model in gen.VOLC_MODEL_CHAIN:
            for value in ("2048x2048", "2560*1440", "4096×4096", "8192x512"):
                self.assertIn("x", gen.normalize_volc_size(value, model))
            for value in ("1500x1500", "8192x8192", "32768x128", "0x2048", "auto"):
                with self.subTest(value=value), self.assertRaises(SystemExit):
                    gen.normalize_volc_size(value, model)
        self.assertEqual(gen.normalize_volc_size("3K", gen.VOLC_MODEL_CHAIN[0]), "3K")
        self.assertEqual(gen.normalize_volc_size("3K", gen.VOLC_MODEL_CHAIN[1]), "3072x3072")
        self.assertEqual(gen.normalize_volc_size("4K", gen.VOLC_MODEL_CHAIN[1]), "4K")

    def test_payload_and_references(self):
        payload = gen.build_volc_payload(self.args(), gen.VOLC_MODEL_CHAIN[0])
        self.assertEqual(payload["size"], "2048x2048")
        self.assertEqual(payload["sequential_image_generation"], "disabled")
        self.assertEqual(payload["response_format"], "url")
        self.assertFalse(payload["watermark"])
        self.assertNotIn("parameters", payload)
        self.assertNotIn("image", payload)
        refs = ["https://example.com/a.png", "data:image/png;base64,AA=="]
        payload = gen.build_volc_payload(self.args(image=refs[0]), gen.VOLC_MODEL_CHAIN[0])
        self.assertEqual(payload["image"], refs[0])
        payload = gen.build_volc_payload(self.args(image=refs[0], image2=refs[1]), gen.VOLC_MODEL_CHAIN[0])
        self.assertEqual(payload["image"], refs)
        for options in ({"seed": 1}, {"prompt_extend": True}):
            with self.assertRaises(SystemExit):
                gen.build_volc_payload(self.args(**options), gen.VOLC_MODEL_CHAIN[0])

    def test_model_fallback_records_actual_model(self):
        with tempfile.TemporaryDirectory() as directory, \
             mock.patch.dict(os.environ, _env(AWK_GEN_KEY="volc", AWK_API_KEY="plan"), clear=True), \
             mock.patch.object(sys, "argv", ["gen", "--prompt", "test", "--out-dir", directory]), \
             mock.patch.object(gen, "api_request", side_effect=[gen.ImgGenHTTPError(404, "not found"),
                               {"data": [{"url": "https://example.com/a.jpg"}]}]) as request, \
             mock.patch.object(gen, "download_image") as download:
            gen.main()
            self.assertEqual([call.args[1]["model"] for call in request.call_args_list], gen.VOLC_MODEL_CHAIN)
            for call in request.call_args_list:
                self.assertEqual(call.args[0], "https://ark.cn-beijing.volces.com/api/v3/images/generations")
                self.assertEqual(call.args[2], "volc")
            record = json.loads((Path(directory) / "prompts.json").read_text())["0"]
            self.assertEqual(record["model"], gen.VOLC_MODEL_CHAIN[1])
            self.assertEqual(record["provider_mode"], "volc")
            self.assertTrue(download.call_args.kwargs["normalize_png"])

    def test_explicit_model_or_bad_parameters_never_retry(self):
        for extra, code in ((["--model", "custom-model"], 404), ([], 400), ([], 429)):
            with tempfile.TemporaryDirectory() as directory, \
                 mock.patch.dict(os.environ, _env(AWK_GEN_KEY="volc", AWK_API_KEY="plan"), clear=True), \
                 mock.patch.object(sys, "argv", ["gen", "--prompt", "test", "--out-dir", directory] + extra), \
                 mock.patch.object(gen, "api_request", side_effect=gen.ImgGenHTTPError(code, "invalid")) as request:
                with self.assertRaises(SystemExit):
                    gen.main()
                self.assertEqual(request.call_count, 1)

    def test_download_converts_jpeg_to_png(self):
        from PIL import Image
        buffer = io.BytesIO()
        Image.new("RGB", (20, 20), "red").save(buffer, format="JPEG")
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = buffer.getvalue()
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(gen.urllib.request, "urlopen", return_value=response):
            path = Path(directory) / "00.png"
            gen.download_image("https://example.com/a.jpg", path, normalize_png=True)
            with Image.open(path) as image:
                self.assertEqual(image.format, "PNG")
                self.assertEqual(image.size, (20, 20))


if __name__ == "__main__":
    unittest.main()
