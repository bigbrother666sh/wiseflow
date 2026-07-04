#!/usr/bin/env python3
"""upload-drive.py — 企业微信微盘文件上传（图片/视频）

Usage: python3 upload-drive.py <file_path> <spaceid> <fatherid>

环境变量（优先本地直连）：
  本地直连：WXWORK_CORP_ID + WXWORK_CORP_SECRET
  relay  ：WXWORK_PROXY_URL + WENYAN_API_KEY

依赖（本地直连视频上传额外需要）：pip install requests
"""

import sys
import os
import hashlib
import base64
import json
import subprocess


def die(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def http_get_json(url):
    import urllib.request
    with urllib.request.urlopen(url) as r:
        return json.loads(r.read())


def is_video(path):
    return path.lower().endswith(('.mp4', '.mov', '.avi', '.wmv'))


def upload_relay(file_path, spaceid, fatherid, proxy_url, api_key):
    endpoint = "upload-video" if is_video(file_path) else "upload-image"
    file_name = os.path.basename(file_path)
    cmd = [
        "curl", "-sf", "--max-time", "300",
        "-X", "POST", f"{proxy_url}/wxwork/drive/{endpoint}",
        "-H", f"x-api-key: {api_key}",
        "-F", f"file=@{file_path}",
        "-F", f"spaceid={spaceid}",
        "-F", f"fatherid={fatherid}",
    ]
    if is_video(file_path):
        cmd += ["-F", f"file_name={file_name}"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        die(f"curl 失败: {result.stderr}")
    d = json.loads(result.stdout)
    if not d.get("ok"):
        die(f"上传失败: {d}")
    return d


def get_token(corp_id, corp_secret):
    d = http_get_json(
        f"https://qyapi.weixin.qq.com/cgi-bin/gettoken"
        f"?corpid={corp_id}&corpsecret={corp_secret}"
    )
    if d.get("errcode", 0) != 0:
        die(f"获取 token 失败: {d.get('errmsg')}")
    return d["access_token"]


def upload_image_local(file_path, spaceid, fatherid, token):
    cmd = [
        "curl", "-sf",
        "-X", "POST",
        f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload"
        f"?access_token={token}&spaceid={spaceid}&fatherid={fatherid}",
        "-F", f"file=@{file_path}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        die(f"curl 失败: {result.stderr}")
    d = json.loads(result.stdout)
    if d.get("errcode", 0) != 0:
        die(f"上传失败: {d}")
    return {"ok": True, "fileid": d["fileid"], "fast_forward": False}


def upload_video_local(file_path, spaceid, fatherid, token):
    try:
        import requests
    except ImportError:
        die("本地直连视频上传需要 requests：pip install requests")

    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)
    CHUNK = 2 * 1024 * 1024  # 2MB

    print(f">>> 计算 SHA1（{file_size // 1024 // 1024} MB）...")
    block_shas = []
    cum = hashlib.sha1()
    with open(file_path, "rb") as f:
        offset = 0
        while offset < file_size:
            chunk = f.read(CHUNK)
            cum.update(chunk)
            block_shas.append(cum.copy().hexdigest())
            offset += len(chunk)

    print(">>> 初始化分块上传...")
    init = requests.post(
        f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload_init"
        f"?access_token={token}",
        json={
            "spaceid": spaceid, "fatherid": fatherid,
            "file_name": file_name, "size": file_size,
            "block_sha": block_shas,
        },
    ).json()
    if init.get("errcode", 0) != 0:
        die(f"init 失败: {init}")
    if init.get("hit_exist"):
        return {"ok": True, "fileid": init["fileid"], "fast_forward": True}

    upload_key = init["upload_key"]
    total = len(block_shas)
    print(f">>> 上传 {total} 块...")
    with open(file_path, "rb") as f:
        for idx in range(1, total + 1):
            chunk = f.read(CHUNK)
            part = requests.post(
                f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload_part"
                f"?access_token={token}",
                json={
                    "upload_key": upload_key,
                    "index": idx,
                    "file_base64_content": base64.b64encode(chunk).decode(),
                },
            ).json()
            if part.get("errcode", 0) != 0:
                die(f"块 {idx} 失败: {part}")
            print(f"    {idx}/{total}")

    print(">>> 完成合并...")
    finish = requests.post(
        f"https://qyapi.weixin.qq.com/cgi-bin/wedrive/file_upload_finish"
        f"?access_token={token}",
        json={"upload_key": upload_key},
    ).json()
    if finish.get("errcode", 0) != 0:
        die(f"finish 失败: {finish}")
    return {"ok": True, "fileid": finish["fileid"], "fast_forward": False}


def main():
    if len(sys.argv) < 4:
        die("Usage: python3 upload-drive.py <file_path> <spaceid> <fatherid>")

    file_path, spaceid, fatherid = sys.argv[1], sys.argv[2], sys.argv[3]

    if not os.path.isfile(file_path):
        die(f"文件不存在: {file_path}")

    ftype = "视频" if is_video(file_path) else "图片"

    corp_id = os.environ.get("WXWORK_CORP_ID", "")
    corp_secret = os.environ.get("WXWORK_CORP_SECRET", "")
    proxy_url = os.environ.get("WXWORK_PROXY_URL", "")
    api_key = os.environ.get("WENYAN_API_KEY", "")

    if corp_id and corp_secret:
        mode = "local"
    elif proxy_url and api_key:
        mode = "relay"
    else:
        die(
            "请配置环境变量：\n"
            "  本地直连：WXWORK_CORP_ID + WXWORK_CORP_SECRET\n"
            "  relay  ：WXWORK_PROXY_URL + WENYAN_API_KEY"
        )

    print(f">>> 模式: {mode}  类型: {ftype}")
    print(f">>> 文件: {file_path}")

    if mode == "relay":
        result = upload_relay(file_path, spaceid, fatherid, proxy_url, api_key)
    else:
        token = get_token(corp_id, corp_secret)
        if is_video(file_path):
            result = upload_video_local(file_path, spaceid, fatherid, token)
        else:
            result = upload_image_local(file_path, spaceid, fatherid, token)

    print(json.dumps(result, ensure_ascii=False))
    tag = "（秒传）" if result.get("fast_forward") else ""
    print(f"✓ 上传成功{tag}")
    print(f"  fileid: {result['fileid']}")


if __name__ == "__main__":
    main()
