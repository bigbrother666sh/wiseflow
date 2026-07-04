"""relay_sign.py — client 侧调用 relay sign 服务的统一入口（Python）

产品拆分后签名收敛到 relay（D1）。本模块供 xhs-publish 等 Python skill 共用。
RELAY_BASE_URL + OFB_KEY 由 entrypoint 从 daemon.env 注入（os.environ）。

接口对应 relay 仓 services/sign/：
  POST /api/v1/sign/xhs/headers  → 仅签名
  POST /api/v1/sign/xhs/proxy    → 签名 + 代请求 edith，返回平台原始 JSON
  POST /api/v1/sign/douyin        → 算 a_bogus

todo: 这里还缺一个bilibili签名接口，后续需要加上
"""

import json
import os
from typing import Any

import requests

RELAY_BASE_URL = os.environ.get("RELAY_BASE_URL", "http://localhost:3020")
_TIMEOUT = 30


def _ofb_key() -> str:
    key = os.environ.get("OFB_KEY")
    if not key:
        raise RuntimeError(
            "OFB_KEY 未配置：签名需走 relay，请设置 OFB_KEY 环境变量（见 daemon.env）"
        )
    return key


def _post(path: str, body: dict) -> Any:
    resp = requests.post(
        f"{RELAY_BASE_URL}{path}",
        headers={"Content-Type": "application/json", "X-OFB-Key": _ofb_key()},
        json=body,
        timeout=_TIMEOUT,
    )
    env = resp.json()
    if not resp.ok or not env.get("success"):
        raise RuntimeError(f"relay {path} 失败 ({resp.status_code}): {env.get('error')}")
    return env["data"]


def xhs_headers(
    uri: str,
    cookies: dict,
    payload: dict | None = None,
    params: dict | None = None,
    method: str = "post",
    sign_format: str = "xys",
    x_rap: bool = False,
) -> dict:
    """仅签名，返回完整 headers（含 Cookie / UA / 签名头），client 自行发请求"""
    return _post(
        "/api/v1/sign/xhs/headers",
        {
            "uri": uri,
            "method": method,
            "payload": payload or {},
            "params": params or {},
            "cookies": cookies,
            "sign_format": sign_format,
            "x_rap": x_rap,
        },
    )["headers"]


def xhs_proxy(
    uri: str,
    cookies: dict,
    payload: dict | None = None,
    xsec_token: str | None = None,
    xsec_source: str | None = None,
    sign_format: str = "xys",
    x_rap: bool = False,
) -> Any:
    """签名 + 代请求 edith，返回平台原始 JSON（client 自行 parse）"""
    return _post(
        "/api/v1/sign/xhs/proxy",
        {
            "uri": uri,
            "payload": payload or {},
            "cookies": cookies,
            "xsec_token": xsec_token,
            "xsec_source": xsec_source,
            "sign_format": sign_format,
            "x_rap": x_rap,
        },
    )


def douyin_sign(query_string: str, post_data: str = "", ua: str | None = None) -> str:
    """算 a_bogus（relay 子进程隔离 vendor），client 自行拼 URL 发请求"""
    return _post(
        "/api/v1/sign/douyin",
        {"queryString": query_string, "postData": post_data, "ua": ua},
    )["a_bogus"]
