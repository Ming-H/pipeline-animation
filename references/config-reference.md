# CONFIG 速查（写配置时打开这个）

设计依据见 [design-theory.md](design-theory.md)；出图后的自检见 [verification.md](verification.md)。

## 画布与布局公式（viewBox 1920×1080）

| 元素 | 位置 |
|---|---|
| 主线 y | `620`（N 个节点均匀分布：`x_i = 170 + i * (1660/(N-1))`，如 7 节点 → 170/500/850/1200/1550/…/1830）|
| 支线 y | `≈210`（放支线节点 + 说明框，避开顶部标题区 y≤100）|
| 芯片行 y | `790`（节点下方一排；相邻 w230 节点对应芯片中心间隔 ~115-135px，w≈100-150）|
| 标题/副标题/图例 | y=58/92/48，引擎自动渲染，只需填 title/subtitle/legend |
| 主线边 | 节点右缘→下一节点左缘：`M <x1+w1/2>,620 L <x2-w2/2>,620` |
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

## 分镜写法

- `t` 单调递增；`cap` 换字幕；`on` 数组里的 id 在此刻点亮（node/chip 弹出、edge 画线、flow/orbit 开始流动、metric 起跳、burst 打出）。
- chips 在同一 scene 内自动 180ms 阶梯入场，无需手动错峰。
- metric 的计数起点=所在 scene 的 `t`（`?t=` 跳转时数字仍然时间准确）。
- 最后一帧惯例：`{t:末尾, cap:'—— 流水线持续运行中（↻ 重播）——'}` 无 on。
- 节奏参考：开场 0s → 输入 1.2s → 支线 3.4s → 支线结论 6s → 主线每阶段 +3.5s → 终点 24.4s → 尾帧 30s。

## id 纪律

nodes/edges/flows/orbits/chips/notes/pops/metrics/bursts **所有集合共用一个 id 注册表**，跨集合不能重名（orbit 内部还会派生 `ring-<id>`）。scenes 的 `on:[...]` 靠这些 id 分发。
