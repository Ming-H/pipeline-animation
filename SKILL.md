---
name: pipeline-animation
description: 生成"黑底动效架构图"——单文件 HTML 流水线动画（节点弹出/连线生长/粒子流动/轨道环旋转/数字滚动/字幕分镜），浏览器打开即播，可暂停重播；可一键导出静态海报（2x 高清 PNG）或 MP4 视频。适用于：训练流程图、系统架构图、数据管道图、任何 X→A→B→C→Y 的流程演示。触发词：动画架构图 / 流程动画 / 黑底动效图 / pipeline 动画 / 训练流程可视化 / 系统架构动画 / 流程图海报。
---

# Pipeline Animation · 黑底动效流水线图

单文件 HTML 动画（约 420 行，零依赖），效果对标推特上流行的"dark-mode 架构动图"：
节点弹性入场 → 连线生长 → 粒子沿管线流动 → 虚线轨道环旋转 → 终点冲击波 + 指标数字滚动，底部字幕条按分镜推进。
一次 CONFIG，三种交付：**可交互 HTML（默认）/ 静态海报 PNG / MP4 视频**。

## 核心纪律（先读这个）

1. **模板必须脚本搬字节**：`cp resources/template.html <目标>.html`，绝不用手打/重新生成整个文件（手写会剥行尾空格、漏 CSS 块）。之后只允许用编辑工具替换 `/* ==== CONFIG START ==== */` 到 `/* ==== CONFIG END ==== */` 之间的内容。
2. **引擎勿改**：CONFIG 区之外的所有代码（CSS/引擎/调试钩子/控制按钮）是冻结层。历史 bug 100% 出在引擎层，数据层零 bug——所以引擎冻结、只写配置。
3. **id 全局唯一**：nodes/edges/flows/orbits/chips/notes/pops/metrics/bursts 所有集合共用一个 id 注册表，跨集合不能重名（orbit 内部还会派生 `ring-<id>`）。scenes 的 `on:[...]` 靠这些 id 分发。
4. **只改 CONFIG**，产出即所见：不需要 build、不需要服务器，浏览器直接打开。

## 工作流

```
1. cp resources/template.html <name>.html
2. 编辑 <name>.html：只替换 CONFIG START~END 区块（改标题/nodes/edges/.../scenes）
   ——布局公式、颜色语义、9 集合速查、分镜写法：references/config-reference.md
3. node scripts/lint_config.js <name>.html     # 配置静态检查（E 必须修，W 建议修）
4. 浏览器打开看效果（open <name>.html）；⏸ 暂停 / ↻ 重播
5. 用 ?t=秒 验证关键帧：references/verification.md（截图/DOM 断言/陷阱录）
6. 交付（按需选一或多种）：
   - 单文件 HTML 直接发（可暂停重播）
   - 静态海报：python3 scripts/export_poster.py <name>.html        # 2x→3840×2160 PNG
   - 视频：    python3 scripts/export_mp4.py <name>.html [--fps 24] # X/小红书可发
```

## 按需加载（不要一次全读）

| 文件 | 什么时候读 |
|------|-----------|
| [references/config-reference.md](references/config-reference.md) | 写 CONFIG 时：布局公式 / 六色语义 / 9 集合速查 / 分镜写法 / id 纪律 |
| [references/verification.md](references/verification.md) | 出图后自检：lint 检查项 / ?t= 截图 / DOM 断言 / 海报与 MP4 导出 / 陷阱录 / 已知死路 |
| [references/design-theory.md](references/design-theory.md) | 想理解"为什么这样设计"或要改布局风格时：视觉层级 / 颜色语义学 / 分镜叙事学 / 排版红线 / 工程哲学 |

## 工具箱

- `scripts/lint_config.js` — CONFIG 静态检查（node，E01–E09/W 系列）
- `scripts/screenshot.sh` — `?t=` 时刻截图（验证用）
- `scripts/export_poster.py` — 静态海报导出（Chrome CDP，2x 高清，自动藏控件，自动取末帧）
- `scripts/export_mp4.py` — MP4 导出（Chrome CDP screencast + ffmpeg，真实时间录制保动画）

## 参考

- 完整可跑示例：`examples/r1_pipeline.html`（7 节点主线+支线+双轨道+双指标，含全部 9 集合用法）
- 断网：Google Fonts 回退系统等宽字体，不影响功能（录视频同样适用）
