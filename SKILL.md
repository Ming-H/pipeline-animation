---
name: pipeline-animation
description: 生成"黑底动效架构图"——单文件 HTML 流水线动画（节点弹出/连线生长/粒子流动/轨道环旋转/数字滚动/字幕分镜），浏览器打开即播，可暂停重播。适用于：训练流程图、系统架构图、数据管道图、任何 X→A→B→C→Y 的流程演示。触发词：动画架构图 / 流程动画 / 黑底动效图 / pipeline 动画 / 训练流程可视化 / 系统架构动画。
---

# Pipeline Animation · 黑底动效流水线图

单文件 HTML 动画（约 420 行，零依赖），效果对标推特上流行的"dark-mode 架构动图"：
节点弹性入场 → 连线生长 → 粒子沿管线流动 → 虚线轨道环旋转 → 终点冲击波 + 指标数字滚动，底部字幕条按分镜推进。

## 核心纪律（先读这个）

1. **模板必须脚本搬字节**：`cp resources/template.html <目标>.html`，绝不用手打/重新生成整个文件（手写会剥行尾空格、漏 CSS 块）。之后只允许用编辑工具替换 `/* ==== CONFIG START ==== */` 到 `/* ==== CONFIG END ==== */` 之间的内容。
2. **引擎勿改**：CONFIG 区之外的所有代码（CSS/引擎/调试钩子/控制按钮）是冻结层。历史 bug 100% 出在引擎层，数据层零 bug——所以引擎冻结、只写配置。
3. **id 全局唯一**：nodes/edges/flows/orbits/chips/notes/pops/metrics/bursts 所有集合共用一个 id 注册表，跨集合不能重名（orbit 内部还会派生 `ring-<id>`）。scenes 的 `on:[...]` 靠这些 id 分发。
4. **只改 CONFIG**，产出即所见：不需要 build、不需要服务器，浏览器直接打开。

## 工作流

```
1. cp resources/template.html <name>.html
2. 编辑 <name>.html：只替换 CONFIG START~END 区块（改标题/nodes/edges/.../scenes）
3. node scripts/lint_config.js <name>.html     # 配置静态检查（E 必须修，W 建议修）
4. 浏览器打开看效果（open <name>.html）；⏸ 暂停 / ↻ 重播
5. 用 ?t=秒 验证关键帧（见下方"验证协议"）
6. 交付：单文件直接发；要发 X/小红书视频 → python3 scripts/export_mp4.py <name>.html
```

## 画布与布局公式（viewBox 1920×1080）

| 元素 | 位置 |
|---|---|
| 主线 y | `620`（N 个节点均匀分布：`x_i = 170 + i * (1660/(N-1))`，如 7 节点 → 170/500/850/1200/1550/…/1830）|
| 支线 y | `≈210`（放支线节点 + 说明框，避开顶部标题区 y≤100）|
| 芯片行 y | `790`（节点下方一排；相邻 w230 节点对应芯片中心间隔 ~115-135px，w≈100-150）|
| 标题/副标题/图例 | y=58/92/48，引擎自动渲染，只需填 title/subtitle/legend |
| 主线边 | 节点右缘→下一节点左缘：`M <x1+w1/2>,620 L <x2-w2/2-8>,620` |
| 支线上行边 | 从起点节点顶部 `M <x>,560` 三次贝塞尔 `C` 到支线左侧 `<支线x-w/2-10>,210` |
| 支线回注边 | `dashed:true` + rose 色，从支线底部回到主线节点顶部（表因果/灵感）|
| 轨道环 | 套在"循环型"节点上：`cx/cy`=节点中心，`rx≈160 ry≈92`；双层环用同心椭圆（内层 `reverse:true, speed:-1.3` 反转）|
| 指标 | 终点圆下方：`y=735/765` 两行；burst 圆心=终点圆心 |

## 颜色语义（PAL 固定六色，别造新色）

| 色 | 值 | 语义 |
|---|---|---|
| cyan | #22d3ee | 模型 / 数据 / 最终产出 |
| violet | #a78bfa | 标准 / SFT / 校验 |
| amber | #fbbf24 | 流水线 / RL 循环 / 迭代 |
| rose | #fb7185 | 决策 / 奖励 / 风控 |
| orange | #fb923c | 中间产物 / 数据流 |
| slate | #94a3b8 | 默认边 / 弱文本 |

legend 按本图实际用到的语义子集声明即可。

## CONFIG 速查（9 个集合）

```js
const CONFIG = {
  title, subtitle, legend:[{color,text}],          // 顶部三件套
  nodes:[                                          // 节点（box 或 circle）
    {id,x,y,w,h,color, shape?, title, sub?, sub2?}
    // shape:'circle' 时 w=直径(h忽略)，title/sub 两行大字居中
    // box: title y-24 / sub y+2 / sub2 y+24 三行
  ],
  edges:[ {id, d:'M..L../C..', color?, dashed?, width?, arrow?} ],
    // d 是完整 SVG path；实线=生长动画，dashed=渐显；arrow:false 去箭头
  flows:[ {id, edge:'<边id>', color, n?, speed?, r?} ],      // 粒子沿边循环流动
  orbits:[ {id, cx,cy, rx,ry, color, n?, speed?, r?, reverse?, ring?} ], // 轨道环
  chips:[ {id, x,y, w, color, text} ],                        // 底部小标签 h=30 定死
  notes:[ {id, x,y, w,h, color, dashed?, lines:[{text,size,color,dy}]} ], // 左上角基准说明框
  pops:[ {id, x,y, text, color, size?, anchor?} ],            // 弹出文字标注
  metrics:[ {id, x,y, color?, size?, prefix, to, suffix?, dur?, decimals?, note?} ], // 数字滚动
  bursts:[ {id, x,y, r?, color?} ],                           // 冲击波圆环
  scenes:[ {t, cap:'字幕', on:[id...]} ],                     // 分镜：t 秒时点亮哪些 id
};
```

### 分镜写法

- `t` 单调递增；`cap` 换字幕；`on` 数组里的 id 在此刻点亮（node/chip 弹出、edge 画线、flow/orbit 开始流动、metric 起跳、burst 打出）。
- chips 在同一 scene 内自动 180ms 阶梯入场，无需手动错峰。
- metric 的计数起点=所在 scene 的 `t`（`?t=` 跳转时数字仍然时间准确）。
- 最后一帧惯例：`{t:末尾, cap:'—— 流水线持续运行中（↻ 重播）——'}` 无 on。
- 节奏参考：开场 0s → 输入 1.2s → 支线 3.4s → 支线结论 6s → 主线每阶段 +3.5s → 终点 24.4s → 尾帧 30s。

## 验证协议（每个新图必做）

### 第一步：CONFIG 静态检查（不用开浏览器）

```bash
node scripts/lint_config.js <name>.html   # E=必须修（exit 1），W=建议修
node scripts/lint_config.js --selftest    # 变异测试自检，改脚本本身时才需要
```

检查项：E01 id 重复（含 orbit 派生 `ring-<id>`）｜E02 flows.edge / scenes.on 引用不存在的 id｜E03 同排节点横向净距 <40 叠字｜E04 note 与节点/其他 note 重叠｜E05 芯片相碰（净距 <8）｜E07 scenes.t 非严格递增｜W02 配置了却没被任何 scene 点亮｜W06 整数指标忘配 `decimals:0`｜W08 pop/note 侵入标题区 y≤100｜W09 超出画布 1920×1080。

### 第二步：?t= 关键帧截图

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
常见陷阱：① 节点 x 间距 < w+40 会叠字；② 支线框和说明框重叠（notes 支线右移）；③ 指标小数位忘配 `decimals:0`；④ **DOM 计数必须用 `grep -o … | wc -l`**——`grep -c` 数的是行数，而 JS 创建的元素会序列化在同一行，结果永远是 1（历史假阴性"chips_on=1"的真正根因；此外 headless Chrome 多实例也建议串行跑，避免抢 profile）；⑤ 视觉模型对小字号有 OCR 误读（如 dt→df、保行→保存），且容易被提示词里你的预期描述带偏（只给中性问题），报告异常先回 DOM/像素证据核对再改。

### 第三步（要发视频才做）：MP4 导出

```bash
python3 scripts/export_mp4.py <name>.html [--fps 24] [--duration 秒] [--out x.mp4] [--dom-report]
```

- 原理：Chrome `--remote-debugging-pipe`（原生 CDP，Python 标准库实现）+ `Page.startScreencast` **真实时间**收帧（≈60fps）→ 按时间戳重采样到 --fps → ffmpeg 合成 H.264/yuv420p，1920×1080，X/小红书直接可发。
- **自然播放录制**（绝不带 `?t=`，那会触发 instant 模式灭掉入场动画），完整保留弹性入场/连线生长/粒子流动/轨道旋转；通过 `Runtime.evaluate` 隐藏左上角控制按钮，**引擎零改动**。
- duration 默认 = 最后一个 scene t + 2s；32s@24fps 约需 40 秒渲染、产物约 3.5MB。
- 核验：`--dom-report` 输出结束时点亮数（应=nodes+chips+notes 数）；`ffmpeg -i x.mp4 -vf select=... ` 抽帧目检；稳态两帧应有差异（动画在动）。
- **已知死路，别走**：虚拟时间逐帧截图（`Emulation.setVirtualTimePolicy` + captureScreenshot）——JS 引擎走虚拟钟而 CSS transition 走墙钟，两钟失步，入场动画被斩成跳变（实测像素证据：过渡窗内 0→100% 跳变）。另：无人 attached 时 `--virtual-time-budget` 不泵 rAF，引擎纹丝不动。

## 参考

- 完整可跑示例：`examples/r1_pipeline.html`（7 节点主线+支线+双轨道+双指标，含全部 9 集合用法）
- 工具箱：`scripts/lint_config.js`（CONFIG 静态检查，node）· `scripts/screenshot.sh`（?t= 截图）· `scripts/export_mp4.py`（MP4 导出，Chrome+ffmpeg，Python 标准库）
- 断网：Google Fonts 回退系统等宽字体，不影响功能（录视频同样适用）
