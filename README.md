# pipeline-animation

**单文件 HTML 黑底动效流水线图** —— 训练流程、系统架构、数据管道，任何 X→A→B→C→Y 的流程，一个文件搞定，浏览器打开即播，可暂停重播。零依赖、零构建、零服务器。

对标 X/Twitter 上流行的 dark-mode 架构动图（节点弹性入场 → 连线生长 → 粒子沿管线流动 → 虚线轨道环旋转 → 终点冲击波 + 指标数字滚动，底部字幕条按分镜推进）。

## 效果演示

**DeepSeek-R1 训练流水线**（7 节点主线 + R1-Zero 支线 + 双轨道环 + 双指标滚动）：

https://github.com/Ming-H/pipeline-animation/raw/main/examples/r1_pipeline.mp4

## 5 分钟上手

```bash
# ① 复制模板（必须脚本搬字节，别手打——会剥行尾空格、漏 CSS 块）
cp resources/template.html my_diagram.html

# ② 只编辑 CONFIG START~END 之间的配置：标题/节点/连线/粒子/轨道/芯片/指标/分镜
open my_diagram.html            # 浏览器直接看，⏸ 暂停 / ↻ 重播

# ③ 静态检查 + 关键帧验证
node scripts/lint_config.js my_diagram.html
scripts/screenshot.sh my_diagram.html 27

# ④ 要发 X / 小红书？一条命令出片（1920×1080 H.264，完整保留入场动画）
python3 scripts/export_mp4.py my_diagram.html
```

### 当作 Claude Code / Agent Skill 用

把本目录放进 agent 的 skills 目录（如 `~/.claude/skills/pipeline-animation/`），之后对 agent 说"画一张 XX 训练流程的动画架构图"即可，它会被 `SKILL.md` 里的纪律约束着只改 CONFIG、跑完验证协议再交付。

## 设计纪律：为什么这东西不容易写坏

- **配置 / 引擎分离**：约 420 行引擎（CSS + SVG 渲染 + 动画循环）是冻结层，历史 bug 100% 出在引擎层、数据层零 bug——所以引擎冻结，产出只写 9 个配置集合（`nodes / edges / flows / orbits / chips / notes / pops / metrics / bursts / scenes`）
- **分镜驱动**：`{t, cap, on:[id...]}` 按时间点亮元素，chips 自动阶梯入场，数字滚动与时间轴严格对齐
- **确定性验证协议**：`?t=秒` 调试钩子直达任意时刻、禁用过渡，headless 截图 + DOM 断言（`node on` 计数 = 配置数）逐项核对
- **静态检查前置**：10 条规则（id 重复 / 引用悬空 / 间距叠字 / 重叠 / scenes 递增 / 死元素 / 小数位…）在开浏览器之前就拦住配置错误，自带变异测试自检

## 工具箱

| 脚本 | 依赖 | 作用 |
|---|---|---|
| `scripts/lint_config.js` | node | CONFIG 静态检查（E 必须修 / W 建议修）；`--selftest` 跑 17 项变异测试 |
| `scripts/screenshot.sh` | Chrome | `?t=` 关键帧截图（确定性终态） |
| `scripts/export_mp4.py` | Chrome + ffmpeg | 真实时间 screencast 录制 → 重采样 → H.264 MP4，自动隐藏控制按钮，引擎零改动 |

## 目录结构

```
skill-pipeline-animation/
├── SKILL.md               # Agent Skill 主文档（工作流/布局公式/颜色语义/验证协议）
├── resources/template.html # 引擎模板（CONFIG 区之外冻结）
├── examples/               # 成图成片示例（DeepSeek-R1）
└── scripts/                # lint / 截图 / MP4 导出
```

## 画布与颜色约定（速览）

- viewBox 1920×1080；主线 y=620，支线 y≈210，芯片行 y=790，标题区 y≤100 勿侵占
- 固定六色语义：cyan=模型/数据/产出 · violet=标准/SFT/校验 · amber=循环/迭代 · rose=决策/奖励/风控 · orange=中间产物/数据流 · slate=默认
- 完整布局公式与分镜节奏参考见 `SKILL.md`

## License

MIT
