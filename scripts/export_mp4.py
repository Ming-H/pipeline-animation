#!/usr/bin/env python3
"""
pipeline-animation skill · 导出 MP4 视频

用法:
    python3 scripts/export_mp4.py <动画.html> [--fps 24] [--duration 秒] [--out out.mp4] [--keep-frames 目录]

原理（真实时间 screencast 录制，完整保留入场弹跳/连线生长/粒子流动）:
    Chrome --remote-debugging-pipe 建立原生 CDP 会话（fd3 发命令 / fd4 收事件，\\0 分隔 JSON），
    Page.startScreencast 让页面按真实浏览器节奏自然播放（rAF / CSS transition / 引擎 vt 三钟同步），
    连续收帧 + 逐帧 ack，按时间戳重采样到 --fps 网格，ffmpeg 合成 H.264 (yuv420p)。

    为什么不用虚拟时间（Emulation.setVirtualTimePolicy）逐帧截图：实测该路径下
    JS 引擎走虚拟钟而 CSS transition 走墙钟，入场动画被斩成跳变；screencast 无此问题。

注意:
    - 绝不带 ?t= 参数（那会触发 instant 模式，入场动画全灭）
    - 通过 Runtime.evaluate 隐藏左上角控制按钮，引擎零改动
    - 非字节级确定性（真实时间录制），逐帧内容以 --dom-report / 抽帧目检核验

依赖:
    Google Chrome + ffmpeg，Python 仅标准库。
"""
import argparse
import base64
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time


def find_chrome():
    for p in [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]:
        if os.path.exists(p):
            return p
    w = shutil.which("chrome") or shutil.which("chromium") or shutil.which("google-chrome")
    if w:
        return w
    sys.exit("未找到 Chrome/Chromium，请安装或修改脚本内路径")


def find_ffmpeg():
    w = shutil.which("ffmpeg")
    if not w:
        sys.exit("未找到 ffmpeg（brew install ffmpeg）")
    return w


def guess_duration(html_text):
    """从 CONFIG 的 scenes 里取最后一个 t，+2s 尾帧留白。可用 --duration 覆盖。"""
    m = re.search(r"CONFIG START", html_text)
    m2 = re.search(r"CONFIG END", html_text)
    if m and m2:
        slice_ = html_text[m.end():m2.start()]
        ts = [float(x) for x in re.findall(r"\bt\s*:\s*([0-9.]+)", slice_)]
        if ts:
            return max(ts) + 2.0
    return 30.0


class CDPPipe:
    """Chrome --remote-debugging-pipe 的极简 CDP 客户端（\\0 分隔 JSON，仅本脚本所需）。"""

    def __init__(self, proc):
        self.proc = proc
        self._id = 0
        self._results = {}
        self.events = queue.Queue()
        self._reader = threading.Thread(target=self._read_loop, daemon=True)
        self._reader.start()

    def _read_loop(self):
        buf = b""
        fd = self.proc.evt_fd
        while True:
            try:
                chunk = os.read(fd, 65536)
            except OSError:
                break
            if not chunk:
                break
            buf += chunk
            while b"\0" in buf:
                msg, buf = buf.split(b"\0", 1)
                if not msg:
                    continue
                try:
                    obj = json.loads(msg)
                except json.JSONDecodeError:
                    continue
                if "id" in obj:
                    self._results[obj["id"]] = obj
                else:
                    self.events.put(obj)

    def send(self, method, params=None, session_id=None):
        self._id += 1
        cmd = {"id": self._id, "method": method, "params": params or {}}
        if session_id:
            cmd["sessionId"] = session_id
        os.write(self.proc.cmd_fd, json.dumps(cmd).encode() + b"\0")
        return self._id

    def wait_result(self, rid, timeout=15):
        deadline = time.time() + timeout
        while rid not in self._results:
            if time.time() > deadline:
                raise TimeoutError(f"CDP 命令超时（id={rid}），Chrome 可能已退出")
            time.sleep(0.005)
        obj = self._results.pop(rid)
        if "error" in obj:
            raise RuntimeError(f"CDP 错误: {obj['error']}")
        return obj.get("result", {})

    def call(self, method, params=None, session_id=None, timeout=15):
        return self.wait_result(self.send(method, params, session_id), timeout)

    def wait_event(self, name, timeout=15):
        """仅用于启动阶段（会丢弃其他事件；screencast 收帧请直接消费 self.events）。"""
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                ev = self.events.get(timeout=max(0.005, deadline - time.time()))
            except queue.Empty:
                break
            if ev.get("method") == name:
                return ev
        raise TimeoutError(f"等待事件 {name} 超时")


def launch_chrome(width, height, user_data_dir):
    """把 CDP 管道固定在 fd3(子读命令)/fd4(子写事件) 再启动 Chrome。

    做法：父进程先 dup2 出 fd3/fd4 副本，Popen(pass_fds=(3,4)) 直接继承。
    （不使用 preexec_fn——实测本机 Python/macOS 组合下子进程内 dup2 不生效。）
    """
    # fd3/fd4：被占用则备份（spawn 后还原，不坑调用方），空闲则用 devnull 占坑
    # （防止 os.pipe 恰好落在 3/4 上，把 dup2 目标和管道自己搅在一起）
    backups = {}
    guards = []
    for fd in (3, 4):
        try:
            os.fstat(fd)
            backups[fd] = os.dup(fd)
        except OSError:
            guards.append(os.open(os.devnull, os.O_RDONLY))

    r_cmd, w_cmd = os.pipe()   # 父写命令 → 子读(fd3)
    r_evt, w_evt = os.pipe()   # 子写事件(fd4) → 父读
    os.dup2(r_cmd, 3)          # Chrome 在 fd3 读命令
    os.dup2(w_evt, 4)          # Chrome 往 fd4 写事件
    os.close(r_cmd)
    os.close(w_evt)

    chrome = find_chrome()
    proc = subprocess.Popen(
        [chrome, "--headless=new", "--remote-debugging-pipe",
         f"--user-data-dir={user_data_dir}", "--no-first-run", "--no-default-browser-check",
         "--hide-scrollbars", f"--window-size={width},{height}", "about:blank"],
        pass_fds=(3, 4),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL)
    os.close(3)   # 我们的替身用完即弃，子进程已有副本
    os.close(4)
    for fd, bak in backups.items():   # 还原调用方原本的 fd3/fd4
        os.dup2(bak, fd)
        os.close(bak)
    proc.cmd_fd = w_cmd
    proc.evt_fd = r_evt
    return proc


def render(html_path, fps, duration, out_mp4, keep_frames=None, dom_report=False,
           chrome_w=1920, chrome_h=1080):
    html_path = os.path.abspath(html_path)
    file_url = "file://" + html_path

    tmpdir = keep_frames or tempfile.mkdtemp(prefix="pa_frames_")
    os.makedirs(tmpdir, exist_ok=True)
    user_data = tempfile.mkdtemp(prefix="pa_profile_")
    proc = launch_chrome(chrome_w, chrome_h, user_data)
    cdp = CDPPipe(proc)
    dom_counts = []
    try:
        target = cdp.call("Target.createTarget", {"url": "about:blank"})
        sess = cdp.call("Target.attachToTarget",
                        {"targetId": target["targetId"], "flatten": True})["sessionId"]
        cdp.call("Page.enable", session_id=sess)
        cdp.call("Runtime.enable", session_id=sess)
        cdp.call("Emulation.setDeviceMetricsOverride",
                 {"width": chrome_w, "height": chrome_h, "deviceScaleFactor": 1, "mobile": False},
                 session_id=sess)
        cdp.call("Page.navigate", {"url": file_url}, session_id=sess)
        cdp.wait_event("Page.loadEventFired", timeout=20)
        # 隐藏左上角控制按钮（引擎零改动）
        cdp.call("Runtime.evaluate",
                 {"expression": "document.getElementById('ctrl').style.display='none'"},
                 session_id=sess)

        # 真实时间 screencast 收帧
        cdp.call("Page.startScreencast",
                 {"format": "png", "everyNth": 1, "maxWidth": chrome_w, "maxHeight": chrome_h},
                 session_id=sess)
        raw = []   # (timestamp秒, png字节)
        deadline = time.time() + duration + 1.5
        while time.time() < deadline:
            try:
                ev = cdp.events.get(timeout=0.1)
            except queue.Empty:
                continue
            if ev.get("method") != "Page.screencastFrame":
                continue
            # flatten 模式下 CDP session 在事件封套 ev["sessionId"]；params.sessionId 是
            # screencast 自己的会话号（整数），用于 ack——别拿它当 CDP session 过滤
            if ev.get("sessionId") and ev["sessionId"] != sess:
                continue
            p = ev["params"]
            cdp.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]}, session_id=sess)
            raw.append((p["metadata"]["timestamp"], base64.b64decode(p["data"])))
        cdp.call("Page.stopScreencast", session_id=sess, timeout=5)
        if len(raw) < 4:
            raise RuntimeError(f"screencast 只收到 {len(raw)} 帧，Chrome 可能没有泵动渲染")
        print(f"  收到 {len(raw)} 帧原始画面，重采样到 {fps}fps × {duration}s", file=sys.stderr)

        # 按时间戳重采样到 fps 网格
        raw.sort(key=lambda x: x[0])
        t0 = raw[0][0]
        total = round(duration * fps)
        idx = 0
        for i in range(total):
            target_t = t0 + i / fps
            while idx + 1 < len(raw) and raw[idx + 1][0] <= target_t:
                idx += 1
            with open(os.path.join(tmpdir, f"f_{i:06d}.png"), "wb") as fp:
                fp.write(raw[idx][1])
            if dom_report:
                pass  # DOM 计数见结尾一次性评估
        if dom_report:
            n = cdp.call("Runtime.evaluate",
                         {"expression": "document.querySelectorAll('.node.on,.chip.on').length"},
                         session_id=sess)["result"]["value"]
            print(f"  录制结束时点亮元素数: {n}（应≈全部）", file=sys.stderr)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        shutil.rmtree(user_data, ignore_errors=True)

    ff = find_ffmpeg()
    subprocess.run([ff, "-y", "-framerate", str(fps), "-i", os.path.join(tmpdir, "f_%06d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
                    "-movflags", "+faststart", out_mp4],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(out_mp4)
    if not keep_frames:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return dom_counts


def main():
    ap = argparse.ArgumentParser(description="pipeline-animation 导出 MP4")
    ap.add_argument("html")
    ap.add_argument("--fps", type=float, default=24)
    ap.add_argument("--duration", type=float, default=None, help="默认取 CONFIG 最后一个 scene t + 2s")
    ap.add_argument("--out", default=None)
    ap.add_argument("--keep-frames", default=None, metavar="目录", help="保留帧目录（调试用）")
    ap.add_argument("--dom-report", action="store_true", help="输出录制结束时的点亮元素数")
    args = ap.parse_args()

    with open(args.html, encoding="utf-8") as f:
        duration = args.duration or guess_duration(f.read())
    out = args.out or os.path.splitext(os.path.basename(args.html))[0] + ".mp4"
    render(args.html, args.fps, duration, out, args.keep_frames, args.dom_report)


if __name__ == "__main__":
    main()
