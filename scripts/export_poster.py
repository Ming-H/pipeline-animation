#!/usr/bin/env python3
"""pipeline-animation skill · 海报模式：导出终态静态高清 PNG（2x，3840×2160）

用法:
  python3 scripts/export_poster.py <html文件> [t秒] [输出png]
  python3 scripts/export_poster.py my_diagram.html            → 自动取末帧 t，导出 /tmp/pa_my_diagram_poster.png
  python3 scripts/export_poster.py my_diagram.html 15         → 15s 时刻的海报
  python3 scripts/export_poster.py my_diagram.html 27 out.png → 自定义输出路径

原理:
  - ?t= 调试钩子直达指定时刻（禁用过渡、元素全点亮）
  - Emulation.setDeviceMetricsOverride(deviceScaleFactor=2) 输出 3840×2160
  - Runtime.evaluate 隐藏左上角 ⏸/↻ 控制按钮（引擎零改动，与 export_mp4 同法）
  - Page.captureScreenshot 单帧截取，无需 ffmpeg
依赖: Google Chrome（与 export_mp4.py 共用查找逻辑）
"""
import argparse
import base64
import os
import re
import struct
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from export_mp4 import CDPPipe, launch_chrome  # noqa: E402


def last_scene_t(html_text):
    """取 CONFIG.scenes 最后一个分镜的 t（终态：所有元素已点亮）。"""
    m, m2 = re.search(r"CONFIG START", html_text), re.search(r"CONFIG END", html_text)
    if m and m2:
        ts = [float(x) for x in re.findall(r"\bt\s*:\s*([0-9.]+)", html_text[m.end():m2.start()])]
        if ts:
            return max(ts)
    return None


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None, None
    return struct.unpack(">II", head[16:24])


def export(html_path, t=None, out=None):
    html_path = os.path.abspath(html_path)
    base = os.path.splitext(os.path.basename(html_path))[0]
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    if t is None:
        t = last_scene_t(html)
        if t is None:
            sys.exit("未能从 CONFIG.scenes 解析出 t（检查 CONFIG 是否含 {t:数字,...} 分镜），或用第2个参数显式指定")
        print(f"自动取末帧 t={t}s", file=sys.stderr)
    out = out or f"/tmp/pa_{base}_poster.png"

    user_data = tempfile.mkdtemp(prefix="pa_profile_")
    proc = launch_chrome(1920, 1080, user_data)
    cdp = CDPPipe(proc)
    try:
        target = cdp.call("Target.createTarget", {"url": "about:blank"})
        sess = cdp.call("Target.attachToTarget",
                        {"targetId": target["targetId"], "flatten": True})["sessionId"]
        cdp.call("Page.enable", session_id=sess)
        cdp.call("Runtime.enable", session_id=sess)
        # 2x 缩放：1920×1080 逻辑像素 → 3840×2160 物理像素
        cdp.call("Emulation.setDeviceMetricsOverride",
                 {"width": 1920, "height": 1080, "deviceScaleFactor": 2, "mobile": False},
                 session_id=sess)
        cdp.call("Page.navigate", {"url": f"file://{html_path}?t={t}"}, session_id=sess)
        cdp.wait_event("Page.loadEventFired", timeout=20)
        # 隐藏左上角控制按钮（引擎零改动）
        cdp.call("Runtime.evaluate",
                 {"expression": "document.getElementById('ctrl').style.display='none'"},
                 session_id=sess)
        time.sleep(1.2)  # 字体/布局稳定
        shot = cdp.call("Page.captureScreenshot", {"format": "png"}, session_id=sess)
        with open(out, "wb") as f:
            f.write(base64.b64decode(shot["data"]))
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()

    w, h = png_size(out)
    print(f"海报已导出: {out}" + (f" ({w}×{h})" if w else ""))
    return out


def main():
    ap = argparse.ArgumentParser(description="pipeline-animation 导出静态海报（2x PNG）")
    ap.add_argument("html", help="动画 HTML 文件")
    ap.add_argument("t", nargs="?", type=float, default=None, help="海报时刻（秒），默认取末帧")
    ap.add_argument("out", nargs="?", default=None, help="输出 PNG 路径，默认 /tmp/pa_<name>_poster.png")
    args = ap.parse_args()
    if not os.path.isfile(args.html):
        sys.exit(f"文件不存在: {args.html}")
    export(args.html, args.t, args.out)


if __name__ == "__main__":
    main()
