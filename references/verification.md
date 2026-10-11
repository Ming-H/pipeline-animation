# 验证协议（每个新图必做）

写 CONFIG 见 [config-reference.md](config-reference.md)；设计依据见 [design-theory.md](design-theory.md)。

## 第一步：CONFIG 静态检查（不用开浏览器）

```bash
node scripts/lint_config.js <name>.html   # E=必须修（exit 1），W=建议修
node scripts/lint_config.js --selftest    # 变异测试自检，改脚本本身时才需要
```

检查项：E01 id 重复（含 orbit 派生 `ring-<id>`）｜E02 flows.edge / scenes.on 引用不存在的 id｜E03 同排节点横向净距 <40 叠字｜E04 note 与节点/其他 note 重叠｜E05 芯片相碰（净距 <8）｜E07 scenes.t 非严格递增｜W02 配置了却没被任何 scene 点亮｜W06 整数指标忘配 `decimals:0`｜W08 pop/note 侵入标题区 y≤100｜W09 超出画布 1920×1080。

## 第二步：?t= 关键帧截图

模板自带 `?t=秒` 调试钩子：跳到任意时刻、禁用所有过渡直达终态（headless 截图确定性输出）。

```bash
# 截关键帧（开场后/中段/终态三张）
scripts/screenshot.sh <name>.html 3.4
scripts/screenshot.sh <name>.html 15
scripts/screenshot.sh <name>.html 27   # 终态：所有元素应全部点亮

# DOM 断言（终态时 node/chip 点亮数 = 配置数，指标=终值）
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
"$CHROME" --headless --disable-gpu --virtual-time-budget=6000 \
  --dump-dom "file://$PWD/<name>.html?t=27" 2>/dev/null > /tmp/dom.html
grep -o 'class="node on"' /tmp/dom.html | wc -l   # = nodes 数（必须 -o|wc -l，见陷阱④）
grep -o 'class="chip on"' /tmp/dom.html | wc -l   # = chips 数
grep -o '<指标prefix> [0-9.]*<suffix>' /tmp/dom.html  # = to 值

# JS 报错检查
"$CHROME" --headless --disable-gpu --enable-logging=stderr \
  --virtual-time-budget=6000 --dump-dom "file://$PWD/<name>.html?t=27" 2>&1 \
  | grep -i "uncaught"                          # 应无输出
```

截图给视觉模型核验：节点标题可读、支线/虚线可见、芯片无重叠、指标为终值。

### 常见陷阱

① 节点 x 间距 < w+40 会叠字；② 支线框和说明框重叠（notes 支线右移）；③ 指标小数位忘配 `decimals:0`；④ **DOM 计数必须用 `grep -o … | wc -l`**——`grep -c` 数的是行数，而 JS 创建的元素会序列化在同一行，结果永远是 1（历史假阴性"chips_on=1"的真正根因；此外 headless Chrome 多实例也建议串行跑，避免抢 profile）；⑤ 视觉模型对小字号有 OCR 误读（如 dt→df、保行→保存），且容易被提示词里你的预期描述带偏（只给中性问题），报告异常先回 DOM/像素证据核对再改。

## 第三步（按需）：静态海报导出

```bash
python3 scripts/export_poster.py <name>.html              # 自动取末帧 t，2x → 3840×2160 PNG
python3 scripts/export_poster.py <name>.html 15 out.png   # 指定时刻
```

- `?t=终态` 直达全点亮 + deviceScaleFactor=2 + CDP 隐藏 ⏸/↻ 控件（引擎零改动）。
- 用于 README / 文章配图 / 知乎公众号头图；动图与海报同源不同壳。

## 第四步（要发视频才做）：MP4 导出

```bash
python3 scripts/export_mp4.py <name>.html [--fps 24] [--duration 秒] [--out x.mp4] [--dom-report]
```

- 原理：Chrome `--remote-debugging-pipe`（原生 CDP，Python 标准库实现）+ `Page.startScreencast` **真实时间**收帧（≈60fps）→ 按时间戳重采样到 --fps → ffmpeg 合成 H.264/yuv420p，1920×1080，X/小红书直接可发。
- **自然播放录制**（绝不带 `?t=`，那会触发 instant 模式灭掉入场动画），完整保留弹性入场/连线生长/粒子流动/轨道旋转；通过 `Runtime.evaluate` 隐藏左上角控制按钮，**引擎零改动**。
- duration 默认 = 最后一个 scene t + 2s；32s@24fps 约需 40 秒渲染、产物约 3.5MB。
- 核验：`--dom-report` 输出结束时点亮数（应=nodes+chips+notes 数）；`ffmpeg -i x.mp4 -vf select=... ` 抽帧目检；稳态两帧应有差异（动画在动）。

### 已知死路，别走

- **虚拟时间逐帧截图**（`Emulation.setVirtualTimePolicy` + captureScreenshot）——JS 引擎走虚拟钟而 CSS transition 走墙钟，两钟失步，入场动画被斩成跳变（实测像素证据：过渡窗内 0→100% 跳变）。
- 无人 attached 时 `--virtual-time-budget` 不泵 rAF，引擎纹丝不动。
- 断网：Google Fonts 回退系统等宽字体，不影响功能（录视频同样适用）。
