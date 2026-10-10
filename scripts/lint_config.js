#!/usr/bin/env node
/**
 * pipeline-animation skill · CONFIG 静态检查
 *
 * 用法:
 *   node scripts/lint_config.js <html文件> [更多html...]   # 检查，有问题 exit 1
 *   node scripts/lint_config.js --selftest                 # 自测（变异测试，无依赖）
 *
 * 检查项（对应 SKILL.md "常见陷阱" + id 纪律）:
 *   E01 id 跨集合重复（含 orbit 派生的 ring-<id> 冲突）
 *   E02 flows.edge / scenes.on 引用了不存在的 id
 *   E03 相邻节点横向间距 < 40px（叠字风险）
 *   E04 notes 说明框与节点/其他 notes 重叠
 *   E05 chips 芯片互相重叠（净距 < 8px）
 *   E07 scenes.t 非严格递增 / 为负
 *   W02 配置了却从未被任何 scene 点亮的 id（终态不可见）
 *   W06 metric 的 to 为整数却未配 decimals:0（会显示 "97.0%"）
 *   W08 pop/note 顶部进入标题区（y≤100）
 *   W09 元素超出画布 1920×1080
 */
'use strict';
const fs = require('fs');
const path = require('path');
const vm = require('vm');

/* ---------- 解析：只取 CONFIG START~END 区，vm 求值 ---------- */
function parseConfig(htmlText, fileName = '<html>') {
  const m1 = /CONFIG START/.exec(htmlText), m2 = /CONFIG END/.exec(htmlText);
  if (!m1 || !m2 || m2.index < m1.index) {
    throw new Error(`${fileName}: 找不到 CONFIG START/END 标记`);
  }
  const start = htmlText.lastIndexOf('\n', m1.index) + 1;   // 标记所在行行首（含整行注释，语法完整）
  const end = htmlText.lastIndexOf('\n', m2.index) + 1;     // END 标记行排除在外
  const slice = htmlText.slice(start, end);
  const sandbox = {};
  try {
    vm.runInContext(slice + '\n;__extract = CONFIG;', vm.createContext(sandbox), { timeout: 2000 });
  } catch (e) {
    throw new Error(`${fileName}: CONFIG 区求值失败: ${e.message}`);
  }
  const cfg = sandbox.__extract;
  if (!cfg || typeof cfg !== 'object') throw new Error(`${fileName}: CONFIG 不是对象`);
  return cfg;
}

/* ---------- 检查器 ---------- */
const COLLECTIONS = ['nodes', 'edges', 'flows', 'orbits', 'chips', 'notes', 'pops', 'metrics', 'bursts'];
const CANVAS_W = 1920, CANVAS_H = 1080;

function lint(cfg) {
  const issues = [];
  const E = (code, msg) => issues.push({ level: 'E', code, msg });
  const W = (code, msg) => issues.push({ level: 'W', code, msg });
  const arr = k => (cfg[k] || []);
  const box = (l, r, t, b) => ({ l, r, t, b });
  const overlap = (a, b) => a.l < b.r && b.l < a.r && a.t < b.b && b.t < a.b;

  /* E01 id 注册表（全集合共用）+ orbit 派生 ring-<id> */
  const seen = new Map();
  for (const k of COLLECTIONS) for (const item of arr(k)) {
    const id = item && item.id;
    if (!id) { E('E01', `${k} 里存在缺 id 的条目`); continue; }
    if (seen.has(id)) E('E01', `id "${id}" 重复：${seen.get(id)} 与 ${k}`);
    else seen.set(id, k);
  }
  for (const o of arr('orbits')) {
    const rid = 'ring-' + o.id;
    if (seen.has(rid)) E('E01', `orbit "${o.id}" 派生的 "${rid}" 与已有 id 冲突（${seen.get(rid)}）`);
  }

  /* E02 引用完整性 */
  const edgeIds = new Set(arr('edges').map(e => e.id));
  for (const f of arr('flows')) if (!edgeIds.has(f.edge))
    E('E02', `flow "${f.id}" 引用了不存在的边 "${f.edge}"`);
  for (const sc of arr('scenes')) for (const id of (sc.on || []))
    if (!seen.has(id)) E('E02', `scene t=${sc.t} 的 on 引用了不存在的 id "${id}"`);

  /* W02 死元素：从未被 scene 点亮 → 终态不可见 */
  const lit = new Set();
  arr('scenes').forEach(sc => (sc.on || []).forEach(id => lit.add(id)));
  for (const [id, k] of seen) if (!lit.has(id))
    W('W02', `${k} "${id}" 从未被任何 scene 点亮`);

  /* E03 节点间距（纵向有重叠的才判横向净距） */
  const nodes = arr('nodes').map(n => {
    const h = n.shape === 'circle' ? n.w : (n.h || 0);
    return { id: n.id, ...box(n.x - n.w / 2, n.x + n.w / 2, n.y - h / 2, n.y + h / 2) };
  });
  for (let i = 0; i < nodes.length; i++) for (let j = i + 1; j < nodes.length; j++) {
    const a = nodes[i], b = nodes[j];
    if (!(a.t < b.b && b.t < a.b)) continue;
    const gap = Math.max(a.l, b.l) - Math.min(a.r, b.r);
    if (gap < 40) E('E03', `节点 "${a.id}" 与 "${b.id}" 横向净距 ${Math.round(gap)}px < 40（叠字风险）`);
  }

  /* E04 notes 与节点/其他 notes 重叠 */
  const noteBoxes = arr('notes').map(n => ({ id: n.id, ...box(n.x, n.x + n.w, n.y, n.y + n.h) }));
  for (const nb of noteBoxes) {
    for (const nd of nodes) if (overlap(nb, nd))
      E('E04', `note "${nb.id}" 与节点 "${nd.id}" 重叠`);
    for (const nb2 of noteBoxes) if (nb2.id !== nb.id && overlap(nb, nb2))
      E('E04', `note "${nb.id}" 与 note "${nb2.id}" 重叠`);
  }

  /* E05 chips 互相重叠（净距 < 8 视为叠） */
  const chipBoxes = arr('chips').map(c => ({ id: c.id, ...box(c.x - c.w / 2, c.x + c.w / 2, c.y - 15, c.y + 15) }));
  for (let i = 0; i < chipBoxes.length; i++) for (let j = i + 1; j < chipBoxes.length; j++) {
    const a = chipBoxes[i], b = chipBoxes[j];
    if (!(a.t < b.b && b.t < a.b)) continue;
    const gap = Math.max(a.l, b.l) - Math.min(a.r, b.r);
    if (gap < 8) E('E05', `chip "${a.id}" 与 "${b.id}" 净距 ${Math.round(gap)}px（< 8，视觉相碰）`);
  }

  /* E07 scenes.t 严格递增且非负 */
  const ts = arr('scenes').map(s => s.t);
  if (ts.length && ts[0] < 0) E('E07', `首个 scene t=${ts[0]} 为负`);
  for (let i = 1; i < ts.length; i++)
    if (!(ts[i] > ts[i - 1])) E('E07', `scenes.t 必须严格递增：t=${ts[i - 1]} 之后出现 t=${ts[i]}`);

  /* W06 整数指标忘配 decimals:0 */
  for (const m of arr('metrics'))
    if (Number.isInteger(m.to) && m.decimals === undefined)
      W('W06', `metric "${m.id}" to=${m.to} 是整数，未配 decimals:0，会显示 "${m.to.toFixed(1)}"`);
    else if (m.decimals === undefined && !Number.isInteger(m.to) && Math.round(m.to) === m.to)
      W('W06', `metric "${m.id}" to=${m.to} 数值上等于整数，未配 decimals`);

  /* W08 pop/note 进入标题区（y≤100 有标题/副标题/图例） */
  for (const p of arr('pops')) if (p.y <= 100)
    W('W08', `pop "${p.id}" y=${p.y} 进入标题区（≤100，与标题/图例相碰）`);
  for (const nb of noteBoxes) if (nb.t <= 100)
    W('W08', `note "${nb.id}" 顶边 y=${nb.t} 进入标题区（≤100）`);

  /* W09 元素超出画布 */
  const allBoxes = [
    ...nodes.map(n => ({ id: n.id, kind: 'node', ...n })),
    ...chipBoxes.map(c => ({ id: c.id, kind: 'chip', ...c })),
    ...noteBoxes.map(n => ({ id: n.id, kind: 'note', ...n })),
  ];
  for (const b of allBoxes)
    if (b.l < 0 || b.r > CANVAS_W || b.t < 0 || b.b > CANVAS_H)
      W('W09', `${b.kind} "${b.id}" 超出画布 1920×1080（${Math.round(b.l)},${Math.round(b.t)} ~ ${Math.round(b.r)},${Math.round(b.b)}）`);

  return issues;
}

/* ---------- 输出 ---------- */
function fmt(issue) {
  return `  [${issue.level}] ${issue.code} ${issue.msg}`;
}
function lintFile(f) {
  const cfg = parseConfig(fs.readFileSync(f, 'utf8'), f);
  return lint(cfg);
}
function report(f, issues) {
  if (issues.length === 0) { console.log(`✓ ${f}`); return true; }
  console.log(`✗ ${f}`);
  issues.forEach(i => console.log(fmt(i)));
  return false;
}

/* ---------- 自测：变异测试 ---------- */
function deepClone(o) { return JSON.parse(JSON.stringify(o)); }

const GOOD_BASE = {
  title: 't', subtitle: 's', legend: [{ color: 'cyan', text: '模型' }],
  nodes: [
    { id: 'in', x: 400, y: 620, w: 200, h: 120, color: 'cyan', title: '输入', sub: '数据源' },
    { id: 's1', x: 850, y: 620, w: 230, h: 130, color: 'violet', title: '① 阶段', sub: '描述', sub2: '补充' },
    { id: 'out', x: 1300, y: 620, w: 160, h: 160, color: 'cyan', shape: 'circle', title: '产出' },
  ],
  edges: [
    { id: 'e1', d: 'M 505,620 L 730,620' },
    { id: 'e2', d: 'M 970,620 L 1215,620' },
  ],
  flows: [
    { id: 'f1', edge: 'e1', color: 'cyan', n: 4, speed: 0.2 },
    { id: 'f2', edge: 'e2', color: 'violet', n: 4, speed: 0.2 },
  ],
  orbits: [{ id: 'o1', cx: 850, cy: 620, rx: 160, ry: 92, color: 'amber', n: 3, speed: 1.0 }],
  chips: [{ id: 'c1', x: 850, y: 790, w: 150, color: 'rose', text: '关键参数' }],
  notes: [{ id: 'nt1', x: 700, y: 180, w: 300, h: 66, color: 'rose', dashed: true,
    lines: [{ text: '第一行', size: 12.5, color: '#fda4af', dy: 28 }] }],
  pops: [{ id: 'p1', x: 850, y: 150, text: '✨ 标注', color: 'amber', size: 15 }],
  metrics: [{ id: 'm1', x: 1300, y: 735, color: 'cyan', size: 15, prefix: '指标 ', to: 97.3, suffix: '%', dur: 1.8 }],
  bursts: [{ id: 'b1', x: 1300, y: 620, r: 72, color: 'cyan' }],
  scenes: [
    { t: 0, cap: '开场' },
    { t: 1.2, cap: '输入', on: ['in'] },
    { t: 3.5, cap: '阶段', on: ['s1', 'e1', 'f1', 'o1', 'c1'] },
    { t: 7.0, cap: '产出', on: ['out', 'e2', 'f2', 'p1', 'nt1', 'm1', 'b1'] },
  ],
};

const MUTATIONS = [
  {
    code: 'E01', desc: 'chip 与 node 重名',
    make(cfg) { cfg.chips[0].id = 'in'; },
  },
  {
    code: 'E01', desc: 'id 与 orbit 派生 ring-<id> 冲突',
    make(cfg) { cfg.nodes[0].id = 'ring-o1'; },
  },
  {
    code: 'E02', desc: 'flow 引用不存在的边',
    make(cfg) { cfg.flows[0].edge = 'e-nope'; },
  },
  {
    code: 'E02', desc: 'scene.on 引用不存在的 id',
    make(cfg) { cfg.scenes[2].on = ['s1', 'ghost']; },
  },
  {
    code: 'E03', desc: '相邻节点横向间距 < 40',
    make(cfg) { cfg.nodes[1].x = 640; }, // in右缘500, s1左缘640-115=525 → 净距25 <40 ✓
  },
  {
    code: 'E04', desc: 'note 与主节点重叠',
    make(cfg) { cfg.notes[0] = { id: 'nt1', x: 800, y: 560, w: 300, h: 66, color: 'rose', lines: [] }; },
  },
  {
    code: 'E05', desc: '两枚芯片重叠',
    make(cfg) { cfg.chips.push({ id: 'c2', x: 910, y: 790, w: 150, color: 'amber', text: 'x' }); }, // c1右缘925 > c2左缘835
  },
  {
    code: 'E07', desc: 'scenes.t 递减',
    make(cfg) { cfg.scenes[2].t = 1.0; },
  },
  {
    code: 'W02', desc: '元素从未被 scene 点亮',
    make(cfg) { cfg.scenes[3].on = cfg.scenes[3].on.filter(id => id !== 'b1'); },
  },
  {
    code: 'W06', desc: '整数指标忘配 decimals:0',
    make(cfg) { cfg.metrics[0].to = 100; },
  },
  {
    code: 'W08', desc: 'pop 进入标题区',
    make(cfg) { cfg.pops[0].y = 90; },
  },
  {
    code: 'W09', desc: '节点超出画布',
    make(cfg) { cfg.nodes[2].x = 1900; }, // circle r=80 → 右缘1980 > 1920
  },
];

function selftest() {
  let pass = 0, fail = 0;
  const t = (name, ok, detail = '') => {
    if (ok) { pass++; console.log(`  ✓ ${name}`); }
    else { fail++; console.log(`  ✗ ${name}${detail ? ' — ' + detail : ''}`); }
  };

  /* 解析层：必须只求值 CONFIG 区（区外有会抛错的引擎代码） */
  console.log('[parse]');
  const htmlFixture = `<!DOCTYPE html><html><body><script>
/* ==================== CONFIG START ==== */
const CONFIG = ${JSON.stringify(GOOD_BASE, null, 1)};
/* ==================== CONFIG END ==== */
const $=s=>document.querySelector(s); $.x.y.z(); // 区外代码，若被求值会崩
</script></body></html>`;
  let parsed = null, parseErr = null;
  try { parsed = parseConfig(htmlFixture, 'fixture'); } catch (e) { parseErr = e; }
  t('CONFIG 区可解析且区外代码不执行', !!parsed && !parseErr && parsed.nodes.length === 3,
    parseErr ? parseErr.message : '');
  t('缺失标记时报错', (() => { try { parseConfig('no markers here', 'x'); return false; } catch { return true; } })());

  /* 检查层：GOOD 必须干净，每个变异必须抓到对应 code */
  console.log('[lint]');
  const baseIssues = lint(deepClone(GOOD_BASE));
  t('基准配置 0 问题', baseIssues.length === 0, JSON.stringify(baseIssues.map(i => i.code)));

  for (const m of MUTATIONS) {
    const cfg = deepClone(GOOD_BASE);
    m.make(cfg);
    const codes = lint(cfg).map(i => i.code);
    t(`${m.code} 抓到「${m.desc}」`, codes.includes(m.code), `实际: [${codes.join(',')}]`);
  }

  /* 真实 example 必须干净 */
  console.log('[examples]');
  const here = path.dirname(__filename);
  for (const ex of ['../examples/r1_pipeline.html']) {
    const f = path.join(here, ex);
    try {
      const issues = lintFile(f);
      t(`${path.basename(f)} 干净`, issues.length === 0, issues.map(i => i.code).join(','));
    } catch (e) { t(`${path.basename(f)} 可解析`, false, e.message); }
  }

  console.log(`\nselftest: ${pass} passed, ${fail} failed`);
  process.exit(fail ? 1 : 0);
}

/* ---------- main ---------- */
const args = process.argv.slice(2);
if (args.includes('--selftest')) selftest();
else if (args.length === 0) {
  console.error('用法: node lint_config.js <html文件>... | --selftest');
  process.exit(2);
} else {
  let allOk = true;
  for (const f of args) {
    try { allOk = report(f, lintFile(f)) && allOk; }
    catch (e) { console.error(`✗ ${e.message}`); allOk = false; }
  }
  process.exit(allOk ? 0 : 1);
}
