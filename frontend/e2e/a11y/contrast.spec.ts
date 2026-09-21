/**
 * 运行时对比度闸（WCAG 2.1 AA）
 * ============================================================================
 * 为什么需要这一道，而不是只靠 scripts/check-contrast.mjs：
 *
 * check-contrast.mjs 在 **token 层**做笛卡尔积（文本层 × 表面层），它能守住
 * "某个 token 被改坏了"，但有三类问题它从结构上就看不见：
 *
 *   1. **第三方组件的样式**。reactflow 的 attribution 写死 `color:#999`，
 *      不经过我们的任何 token —— token 级闸永远发现不了它。（C 批次实测 2.72:1）
 *   2. **组件把弱文本层级放在了非标准的底上**。比如分段控件的轨道用
 *      bg-surface-hover，未激活文字用 text-text-tertiary，浅色只有 4.34:1。
 *      token 级闸会把这类记为"已知债务"（因为它分不清是取值错还是用法错），
 *      于是真实实例一直存在却不拦构建。
 *   3. **只在特定数据形态下才渲染的分支**。cases 详情的 SLA 字段只有
 *      `expired` 时才套红色，换个数据集就查不到；`urgent` 分支更是长期没数据命中，
 *      浅色下 3.19:1 的 text-amber-600 一直躺在那里。
 *
 * 所以这道闸在**真实渲染结果**上做断言：遍历页面上每一个可见文本节点，
 * 用它的 computed color 与逐层求出的有效背景色算对比度。这与人工审计用的是同一套
 * 算法，只是搬进了测试里 —— 从此不必每次手写一遍审计脚本。
 *
 * 判定规则（WCAG 2.1 AA，1.4.3）：
 *   - 正文（< 24px，或 < 18.66px 的非粗体）≥ 4.5:1
 *   - 大字（≥ 24px，或 ≥ 18.66px 且 bold）≥ 3:1
 *   - 非激活控件（disabled / aria-disabled）按规范豁免，直接跳过
 *   - aria-hidden、不可见、opacity:0 的元素跳过
 *
 * 失败时输出：文本片段 / 实测值 / 要求值 / computed color / className，
 * 足以直接定位到组件。
 * ============================================================================
 */

import { test, expect, type Page } from "@playwright/test";
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { login, TEST_USERS } from "../utils/auth";

/**
 * 待审计的页面。列表页 + 新建类页面是静态的；详情页的 ID 在运行时发现。
 *
 * 覆盖面原则：**把 app/[locale] 下所有可达页面都放进来**，不留"以后再说"。
 * 历史证明静态统计排不出优先级 —— `threat-hunting`（46 处）与 `monitor`（284 处）
 * 都是跑出来才发现的，按硬编码色数量排序时它们根本不显眼。
 *
 * 刻意排除的只有两类：
 *   · `/[...rest]` —— 404 兜底页，不是正常入口。
 *   · `/login` —— 未登录态页面，而本闸全程在登录态下运行，访问它会被重定向，
 *     审计到的其实是别的页面（假通过）。需要单独一条未登录用例，见文件末尾说明。
 *
 * 另外注意**重定向会造成重复计数**，下面三对是同一个页面，只保留落点：
 *   /admin/health   → /admin/dashboard
 *   /admin/settings → /settings/system
 *   /admin/audit    → /audit
 */
const STATIC_PAGES: Array<{ label: string; path: string }> = [
  // ── 概览与运营 ─────────────────────────────────────────────
  { label: "仪表盘", path: "/" },
  { label: "告警列表", path: "/alerts" },
  { label: "工单列表", path: "/cases" },
  { label: "剧本列表", path: "/playbooks" },
  { label: "剧本定义", path: "/playbooks/definitions" },
  { label: "剧本审批", path: "/playbooks/approvals" },
  { label: "剧本新建", path: "/playbooks/create" },
  { label: "威胁狩猎", path: "/threat-hunting" },
  { label: "触发器", path: "/triggers" },
  { label: "监控总览", path: "/monitor" },
  // ── 安全能力 ───────────────────────────────────────────────
  { label: "资产管理", path: "/assets" },
  { label: "云原生", path: "/cloud-native" },
  { label: "关联分析", path: "/correlation" },
  { label: "威胁情报", path: "/threat-intel" },
  { label: "情报看板", path: "/threat-intel/dashboard" },
  { label: "UEBA", path: "/ueba" },
  { label: "插件市场", path: "/marketplace" },
  { label: "报表", path: "/reports" },
  // ── AI ────────────────────────────────────────────────────
  { label: "AI 助手", path: "/ai-assistant" },
  // ── 管理（落点，非重定向源）────────────────────────────────
  { label: "审计日志", path: "/audit" },
  { label: "管理仪表盘", path: "/admin/dashboard" },
  { label: "密钥管理", path: "/admin/secrets" },
  { label: "用户管理", path: "/admin/users" },
  { label: "系统配置", path: "/settings/system" },
  // ── 设置 ──────────────────────────────────────────────────
  { label: "设置", path: "/settings" },
  { label: "AI 模型设置", path: "/settings/ai-models" },
  { label: "API 密钥设置", path: "/settings/api-keys" },
  { label: "通知设置", path: "/settings/notifications" },
  { label: "修改密码", path: "/change-password" },
  // ── 触发器新建 ─────────────────────────────────────────────
  { label: "Cron 新建", path: "/triggers/cron/new" },
  { label: "Webhook 新建", path: "/triggers/webhook/new" },
];

const THEMES = ["light", "dark"] as const;
type ThemeName = (typeof THEMES)[number];

interface Failure {
  text: string;
  ratio: number;
  required: number;
  color: string;
  background: string;
  fontSize: string;
  className: string;
  path: string;
}

/** 浏览器侧：遍历可见文本节点并按 AA 判定。 */
function collectFailures(): { failures: Failure[]; gradientSkipped: number } {
  type RGB = { r: number; g: number; b: number; a: number };

  const parse = (value: string): RGB | null => {
    const m = String(value).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1]
      .split(/[,\s/]+/)
      .filter(Boolean)
      .map(parseFloat);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };

  const lum = (c: RGB): number => {
    const f = (v: number) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };

  const composite = (fg: RGB, bg: RGB): RGB => ({
    r: fg.r * fg.a + bg.r * (1 - fg.a),
    g: fg.g * fg.a + bg.g * (1 - fg.a),
    b: fg.b * fg.a + bg.b * (1 - fg.a),
    a: 1,
  });

  const ratioOf = (a: RGB, b: RGB): number => {
    const la = lum(a);
    const lb = lum(b);
    return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
  };

  const isDark = document.documentElement.classList.contains("dark");

  /**
   * 逐层向上找到候选背景色。
   *
   * 返回**数组**：普通情况下 1 个元素；遇到渐变时返回**所有色标**。
   *
   * 为什么渐变不能简单跳过：渐变的 `background-color` 是透明的，逐层向上找会越过它、
   * 落到几百像素外的祖先 —— 于是"白字压蓝色渐变按钮"被算成"白字压白底 = **1:1**"，
   * 这是个假阳性。但**直接跳过又会丢掉覆盖面**（实测 25 个文本节点）。
   * 正确做法是**按所有色标逐个判、取最差的一个** —— 渐变上任何位置都必须达标。
   *
   * 只有在色标一个都解析不出来时才返回空数组（真正无法判定）。
   */
  const candidateBgs = (el: Element): RGB[] => {
    let n: Element | null = el;
    while (n && n !== document.documentElement) {
      const cur: Element = n;
      const s = getComputedStyle(cur);

      if (s.backgroundImage && s.backgroundImage.includes("gradient")) {
        // 取出该元素之前已经确定的不透明底色，用于给半透明色标做合成
        const stops = (s.backgroundImage.match(/rgba?\([^)]+\)/g) || [])
          .map(parse)
          .filter((c): c is RGB => !!c)
          .map((c) => (c.a < 1 ? composite(c, fallbackBg(cur)) : c));
        if (stops.length > 0) return stops;
        break; // 有渐变但解析不出色标：确实无法判定
      }

      const p = parse(s.backgroundColor);
      if (p && p.a > 0.9) return [p];
      n = n.parentElement;
    }
    return [isDark ? { r: 9, g: 13, b: 22, a: 1 } : { r: 248, g: 250, b: 252, a: 1 }];
  };

  /** 渐变之下的兜底底色（用于合成半透明色标）。 */
  const fallbackBg = (el: Element): RGB => {
    let n: Element | null = el.parentElement;
    while (n && n !== document.documentElement) {
      const s = getComputedStyle(n);
      if (!s.backgroundImage || !s.backgroundImage.includes("gradient")) {
        const p = parse(s.backgroundColor);
        if (p && p.a > 0.9) return p;
      }
      n = n.parentElement;
    }
    return isDark ? { r: 9, g: 13, b: 22, a: 1 } : { r: 248, g: 250, b: 252, a: 1 };
  };

  const out: Failure[] = [];
  let gradientSkipped = 0;
  const nodes = document.querySelectorAll(
    "p,span,h1,h2,h3,h4,h5,h6,a,button,label,td,th,li,dt,dd,code,figcaption,legend,summary"
  );

  for (let i = 0; i < nodes.length; i++) {
    const el = nodes[i];
    // 只审计元素**自己的**文本子节点。
    // ⚠️ 不能写 `if (el.children.length > 0) continue;` —— 那样会把含图标的行
    // （`<p>HASH <ChevronDown/></p>`）整条跳过；也不能用 `el.textContent` 判断，
    // 那会把子元素的文本重复计入。这两条叠加实测造成 15 处漏报。
    const ownText = [...el.childNodes]
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent ?? "")
      .join("")
      .trim();
    // 单字符同样要审：`*` 必填标记实测 3.76:1（旧规则 `length < 2` 会漏掉）。
    if (!ownText) continue;

    const rect = el.getBoundingClientRect();
    if (rect.width < 2 || rect.height < 2) continue;

    const style = getComputedStyle(el);
    if (style.visibility === "hidden" || style.display === "none") continue;
    if (parseFloat(style.opacity) === 0) continue;

    // WCAG 豁免：非激活控件；装饰性内容
    if (el.closest('[disabled],[aria-disabled="true"],[aria-hidden="true"]')) continue;

    const rawFg = parse(style.color);
    if (!rawFg) continue;

    const bgs = candidateBgs(el);
    if (bgs.length === 0) {
      gradientSkipped++;
      continue;
    }

    // 所有候选背景里最差的一个决定结论 —— 渐变上任何位置都必须可读
    let bg = bgs[0];
    let ratio = -1;
    for (const cand of bgs) {
      const fg0 = rawFg.a < 1 ? composite(rawFg, cand) : rawFg;
      const r = ratioOf(fg0, cand);
      if (ratio < 0 || r < ratio) {
        ratio = r;
        bg = cand;
      }
    }

    const size = parseFloat(style.fontSize);
    const weight = parseInt(style.fontWeight, 10) || 400;
    const isLarge = size >= 24 || (size >= 18.66 && weight >= 700);
    const required = isLarge ? 3 : 4.5;

    if (ratio >= required) continue;

    out.push({
      text: ownText.slice(0, 40),
      ratio: Math.round(ratio * 100) / 100,
      required,
      color: style.color,
      background: `rgb(${Math.round(bg.r)}, ${Math.round(bg.g)}, ${Math.round(bg.b)})`,
      fontSize: `${Math.round(size)}px`,
      className: String(el.className).slice(0, 80),
      path: `${location.pathname}#${i}`,
    });
  }

  return { failures: out, gradientSkipped };
}

/** 设主题：注入 zustand persist 的存储值，在页面脚本执行前生效。 */
async function useTheme(page: Page, theme: ThemeName): Promise<void> {
  await page.addInitScript((t: string) => {
    window.localStorage.setItem(
      "theme-storage",
      JSON.stringify({ state: { theme: t }, version: 0 })
    );
  }, theme);
}

/**
 * 带鉴权保证的跳转。
 *
 * 为什么必须有这一层：整批跑（约 2 分钟、几十次登录复用）到末尾时会话会失效，
 * 页面被重定向到 /login。**在登录页上做对比度审计是静默通过**——登录页本身没有对比度
 * 问题，闸会报绿，看起来一切正常。这比"跳过"危险得多，所以这里把它变成**显式失败**。
 *
 * （第一次踩到时的现场：跳过消息里带着 url=/en/login —— 是加在跳过信息里的"现场诊断"
 * 救了一次。教训：闸的跳过/失败信息必须能自证"它真的跑在了目标页面上"。）
 */
async function gotoAuthed(
  page: Page,
  base: string,
  path: string,
  admin: { username: string; password: string }
): Promise<void> {
  let lastUrl = "";
  // 最多两轮：第一轮用当前会话，失败就清 cookie 走一次真实登录再来
  for (let attempt = 1; attempt <= 2; attempt++) {
    await page.goto(`${base}${path}`, { waitUntil: "domcontentloaded" });
    // ⚠️ 不能 goto 后立刻查 URL：本站的鉴权重定向发生在**客户端**（hydrate 之后），
    // 刚 domcontentloaded 时还在目标页，约 1s 后才跳到 /login。
    // 只查一次会漏判，接着审计就跑在登录页上并**静默通过**（这是最危险的失败模式）。
    await page.waitForTimeout(2000);
    lastUrl = page.url();
    if (!/\/login/.test(lastUrl)) return;

    await page.context().clearCookies();
    await login(page, admin.username, admin.password);
  }

  throw new Error(
    `鉴权失败：${path} 最终停在 ${lastUrl}。若继续，审计会跑在登录页上并静默通过，因此直接失败。`
  );
}

/**
 * 等页面文本量稳定下来。
 *
 * ⚠️ 这是本闸修过的最严重的一个自身缺陷：**固定等待会造成假通过**。
 * `monitor` 页在数据到达前几乎是空的，`waitForTimeout(1800)` 时它只有骨架、
 * 没有文字，于是审计"通过"；等数据渲染出来后实测是 **132（浅）/147（深）处不达标**。
 * 也就是说：闸报了绿，而页面是全仓最坏的一页。
 *
 * 做法：轮询 `document.body.innerText.length`，连续两次变化 ≤2 即认为稳定（最多等 8s）。
 * 比 `waitUntil:"networkidle"` 可靠 —— 本站有常驻 WebSocket，networkidle 永不达成。
 */
async function waitForStable(page: Page, timeoutMs = 8000): Promise<void> {
  let prev = -1;
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const len = await page.evaluate(() => document.body.innerText.length);
    if (prev >= 0 && Math.abs(len - prev) <= 2) return;
    prev = len;
    await page.waitForTimeout(500);
  }
}

/**
 * 渲染守卫的阈值。
 *
 * 取值的依据：扩面前对 24 个页面做过一次侦察，实测"可见文本节点数"最低 45、
 * 正文长度也都在数百字以上；而空壳页（骨架屏 / 数据为空 / 权限不足）
 * 通常只有个位数节点、几十字。阈值取在两者之间且明显偏低，宁可漏报也不误报 ——
 * 守卫的目的是拦住"空壳被当成通过"，不是给正常页面设门槛。
 */
const RENDER_GUARD = { minLeaves: 15, minTextLen: 150 };

/** 统计页面上真正可见的叶子文本节点数与正文长度（供渲染守卫判定）。 */
async function measureRendered(page: Page): Promise<{ textLen: number; leaves: number }> {
  return page.evaluate(() => {
    const SEL =
      "p,span,h1,h2,h3,h4,h5,h6,a,button,label,td,th,li,dt,dd,code,figcaption,legend,summary";
    let leaves = 0;
    document.querySelectorAll(SEL).forEach((el) => {
      if (el.children.length > 0) return;
      const t = (el.textContent || "").trim();
      if (t.length < 2) return;
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) return;
      leaves++;
    });
    return { textLen: document.body.innerText.trim().length, leaves };
  });
}

/** 滚动一遍以 materialize 折叠/懒渲染内容，再回到顶部。 */
async function sweep(page: Page): Promise<void> {
  await page.evaluate(async () => {
    const step = window.innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight && y < step * 12; y += step) {
      window.scrollTo(0, y);
      await new Promise((r) => setTimeout(r, 60));
    }
    window.scrollTo(0, 0);
  });
  await page.waitForTimeout(400);
}

/** 一次访问里同时取两样东西：文本对比度失败 + 深色下的大面积浅色表面。 */
interface PageAudit {
  failures: Failure[];
  surfaces: Array<{ tag: string; className: string; background: string; size: string }>;
  /** 因背景是渐变而无法判定的文本节点数（假阳性的来源，需可见） */
  gradientSkipped: number;
}

/**
 * 访问并审计一个页面。
 *
 * 之所以把「浅色表面」和「文本对比度」合在同一次访问里：早期版本在深色轮次跑完之后，
 * 又**完整重访了一遍全部 12 个页面**去采浅色表面。那是纯粹的重复成本 —— 每次
 * `gotoAuthed` 都要等 2s 的客户端鉴权重定向判定，12 个页面就是 24s 的固定开销，
 * 再加上 sweep 与等待稳定，整轮直接翻倍。实测曾因此跑到 20.9 分钟而撞上超时。
 * 同一个页面、同一个 DOM 状态，两次 evaluate 就够了，不需要两次访问。
 */
async function audit(
  page: Page,
  baseUrl: string,
  label: string,
  path: string,
  admin: { username: string; password: string },
  opts: { collectSurfaces?: boolean } = {}
): Promise<PageAudit> {
  await gotoAuthed(page, baseUrl, path, admin);
  await waitForStable(page);
  await sweep(page);
  await waitForStable(page);
  // ⚠️ 鼠标归位必须在**内容渲染完成之后**再派发一次：
  // 登录时点过按钮，指针停在屏幕中部；若那里恰好是表格行，行上的
  // `hover:bg-surface-hover` 会被激活 —— 实测让告警列表多出 2 处、工单列表多出 1 处。
  // 浏览器不会因为"后来才有内容出现在指针下"而重算 :hover，只有新的鼠标事件才会，
  // 所以只在 goto 之后归位一次是不够的。
  await page.mouse.move(2, 2);
  await page.waitForTimeout(250);

  // ⚠️ 渲染守卫：先确认页面真的渲染了内容，再谈对比度。
  // 这是本闸第三个被修掉的假通过模式 —— 前两个是"固定等待导致审计空页"与
  // "被重定向到 /login 却照常审计"。扩面到 30+ 页面之后，风险更大：
  // 任何一个页面只要因为数据为空 / 权限不足 / 仍在加载而渲染成空壳，
  // 审计都会得到"0 处不达标"，看起来像修好了。
  // 这里把它变成显式失败，而不是让闸报绿。
  const rendered = await measureRendered(page);
  if (rendered.leaves < RENDER_GUARD.minLeaves || rendered.textLen < RENDER_GUARD.minTextLen) {
    throw new Error(
      `【这不是对比度结论】${label}（${path}）疑似未渲染完成：` +
        `可见文本节点 ${rendered.leaves} 个、正文 ${rendered.textLen} 字，` +
        `低于守卫阈值 ${RENDER_GUARD.minLeaves} / ${RENDER_GUARD.minTextLen}。\n` +
        `      常见原因：页面仍在加载、数据为空、或该页对当前账号不可见。\n` +
        `      闸在此主动失败 —— 渲染成空壳的页面必然"没有对比度问题"，那是假通过。`
    );
  }

  const { failures, gradientSkipped } = await page.evaluate(collectFailures);
  for (const f of failures) f.text = `[${label}] ${f.text}`;

  // 浅色表面只在深色主题下有意义（判的是"深色界面上出现浅色大块"），
  // 所以仅在深色轮次采集，顺带省掉浅色轮次里的这次 evaluate。
  const surfaces = opts.collectSurfaces
    ? (await page.evaluate(collectLightSurfaces, DARK_SURFACE_ALLOWLIST)).map((s) => ({
        ...s,
        className: `[${label}] ${s.className}`,
      }))
    : [];

  return { failures, surfaces, gradientSkipped };
}

/** 运行时发现详情页 ID —— 否则这类页面根本进不了闸的覆盖面。 */
async function discoverIds(page: Page, baseUrl: string): Promise<Record<string, string>> {
  const ids: Record<string, string> = {};
  try {
    const casesRes = await page.request.get(`${baseUrl}/api/v1/cases?page=1&page_size=5`);
    if (casesRes.ok()) {
      const body = await casesRes.json();
      const list = body?.cases || body?.items || [];
      if (list.length > 0) ids.caseId = list[0].id;
    }
  } catch {
    /* 单页发现失败不应让整道闸失败 */
  }
  try {
    const pbRes = await page.request.get(`${baseUrl}/api/playbook-definitions`);
    if (pbRes.ok()) {
      const body = await pbRes.json();
      const list = Array.isArray(body) ? body : body?.items || [];
      if (list.length > 0) ids.playbookId = list[0].id;
    }
  } catch {
    /* 同上 */
  }
  return ids;
}

/**
 * 深色主题下的「大面积近白表面」判据
 * ============================================================================
 * WCAG 1.4.11 只约束非文本元素的对比度，管不了"第三方组件完全没做主题适配"这种问题。
 * 但这类缺陷的表现高度一致：深色界面上出现一块大面积的浅色矩形 ——
 * 本次就是 reactflow 的 MiniMap（`.react-flow__minimap { background: #fff }`）
 * 在画布右下角留了一块 200×150 的纯白方块。文字审计看不见它，因为那里面没有文字。
 *
 * 阈值是量出来的，不是拍的：在 10 个页面 × 深色下扫「面积 ≥ 4000px²、宽 ≥ 60、高 ≥ 40、
 * 不透明度 ≥ 0.5、相对亮度 ≥ 0.55」的元素，全站恰好命中 1 处（就是那个 MiniMap），
 * 零假阳性 —— 所以可以放心断言。
 *
 * 误报时怎么办：先确认它是不是真的没适配主题。若确有正当理由（例如某处刻意用白底
 * 承载深色插画），把它加进下面的 DARK_SURFACE_ALLOWLIST 并写明原因，不要放宽阈值。
 */
const DARK_SURFACE_ALLOWLIST: string[] = [
  // 二维码容器**必须**保持白底：认证器应用依赖二维码周围的白色静默区才能正确识别，
  // 深色底会让扫描失败。这是有正当理由的例外，不是"漏了主题适配"。
  // 位置：settings/components/TwoFactorSettings.tsx（"Framed QR Container"）。
  "bg-white rounded-2xl shadow-md border border-gray-200/90",
];

// 注意：allowlist 必须作为参数传入。page.evaluate 只序列化函数本身，
// 闭包里的模块级变量在浏览器侧是取不到的（会直接 ReferenceError）。
function collectLightSurfaces(
  allowlist: string[]
): Array<{ tag: string; className: string; background: string; size: string }> {
  const parse = (value: string) => {
    const m = String(value).match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1]
      .split(/[,\s/]+/)
      .filter(Boolean)
      .map(parseFloat);
    return { r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1 };
  };
  const luminance = (c: { r: number; g: number; b: number }) => {
    const f = (v: number) => {
      const s = v / 255;
      return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };

  const out: Array<{ tag: string; className: string; background: string; size: string }> = [];
  const all = document.querySelectorAll("*");
  for (let i = 0; i < all.length; i++) {
    const el = all[i];
    const r = el.getBoundingClientRect();
    if (r.width < 60 || r.height < 40 || r.width * r.height < 4000) continue;
    const style = getComputedStyle(el);
    if (style.visibility === "hidden" || style.display === "none") continue;
    if (parseFloat(style.opacity) === 0) continue;
    const bg = parse(style.backgroundColor);
    if (!bg || bg.a < 0.5) continue;
    if (luminance(bg) < 0.55) continue;
    const className = String(el.className).slice(0, 80);
    if (allowlist.some((s) => className.includes(s))) continue;
    out.push({
      tag: el.tagName,
      className,
      background: style.backgroundColor,
      size: `${Math.round(r.width)}×${Math.round(r.height)}`,
    });
  }
  return out;
}

/**
 * 交互后才出现的状态
 * ============================================================================
 * 静止态遍历看不到这类状态。三条实测来源：
 *
 *   · **切换按钮的非默认面**。`playbooks/create` 与 `definitions/[id]/edit` 的
 *     "立即激活"按钮默认渲染 `已激活`，失败分支 `草稿` 用
 *     `bg-surface-hover … text-text-tertiary`（浅色 4.34:1）—— 只有点一下才出现。
 *   · **数据形态依赖**。`cases/[id]` 的 SLA `urgent` 分支（浅色 3.19:1）要靠特定数据才渲染。
 *   · **折叠面板展开后的内容、多步向导的后几步、条件渲染的提示条**。
 *
 * 这类状态没法用通用遍历覆盖（不能对任意页面乱点按钮），所以用**显式探针**登记：
 * 每条写明页面、主题、就绪锚点、以及让目标状态出现的那一次点击。
 */
interface InteractionProbe {
  label: string;
  /** 支持 {playbookId} 占位，由运行时发现的数据填充 */
  path: string;
  theme: ThemeName;
  /** "表单已加载完成"的标志。编辑页的定义是异步拉的，先等它出现再找目标按钮。 */
  ready: RegExp;
  /** 点它，让目标状态出现 */
  click: RegExp;
}

const INTERACTION_PROBES: InteractionProbe[] = [
  // 正则写成双语：`playbooks/create` 把 "已激活 (Active)" 写死在代码里，
  // 而 `definitions/[id]/edit` 走 t()，跟随语言变化。
  // 注意本文件的页面路径都不带 locale 前缀，会被重定向到**默认语言 en** ——
  // 所以 i18n 化的文案实际渲染成英文（这也是 i18n 泄漏能被发现的原因）。
  {
    label: "剧本新建·草稿态",
    path: "/playbooks/create",
    theme: "light",
    ready: /JSON 源码|JSON Source/,
    click: /已激活|Active/,
  },
  {
    label: "剧本新建·草稿态",
    path: "/playbooks/create",
    theme: "dark",
    ready: /JSON 源码|JSON Source/,
    click: /已激活|Active/,
  },
  {
    label: "剧本编辑·草稿态",
    path: "/playbooks/definitions/{playbookId}/edit",
    theme: "light",
    ready: /保存修改|Save Changes/,
    click: /已激活|草稿|Active|Draft/,
  },
  {
    label: "剧本编辑·草稿态",
    path: "/playbooks/definitions/{playbookId}/edit",
    theme: "dark",
    ready: /保存修改|Save Changes/,
    click: /已激活|草稿|Active|Draft/,
  },
];

/**
 * 运行时对比度债务棘轮
 * ============================================================================
 * 登记在册的存量：按 **(页面, 前景色, 背景色, 字号) 这一「色对」** 分组，
 * 每类给一个 max 上限 —— 命中且数量 ≤ max 则记为已知债务、不阻断；
 * 未命中或超出 max 则阻断构建。
 *
 * **当前为空**：`监控总览` 的 284 处 / 39 类存量已在同批次全部清零
 * （见 优化实施方案.md §16.11–16.12，以及下面这份已归档的清单）。
 * 空表意味着**任何一处新的不达标都会直接阻断** —— 这是这道闸最严的状态。
 *
 * 若将来确需登记新的存量，务必带上：页面、前景、背景、字号、上限、根因，
 * 并把「为什么容忍」和「修复归属」写清楚。**不要放宽全局阈值**，
 * 也不要把不同形状的问题混进同一条（逐条白名单会让新问题也被放过）。
 *
 * ── 已归档：监控总览 284 处 / 39 类（2026-09-19 清零）────────────────────
 * 根因一 · 白字压在 500 级实色胶囊上（MITRE 技术标签）        88 处，最低 1.92:1
 *   → 规则：500 级色只做填充/描边，不做文字底色；文字一律走语义文本色。
 *   → 注：500 级实色存在「亮度死区」（如 #8b5cf6 相对亮度 0.198），
 *     黑白两色文字都无法达到 4.5:1 —— 靠换字色修不好，必须改填充策略。
 * 根因二 · 灰阶微文案未走语义 token（gray-400/500）         102 处，最低 2.54:1
 *   → 改 text-text-tertiary / secondary；承载它们的 bg-gray-* 一并换成 bg-surface-*。
 * 根因三 · 图表内联颜色（blue-400 次级文字、recharts 图例）   38 处，最低 3.19:1
 *   → recharts 默认把系列描边色当图例字色，必须显式传 formatter 覆盖。
 * 根因四 · 徽章色对（red-600 on red-100 等）                  8 处，最低 3.11:1
 *   → 换 severity/status 的 -fg / -bg 槽位。
 * 另：用元素 opacity 表达强度会把文字一起淡掉（本页曾因此掉到 1.92:1），
 *     强度必须走「填充 alpha + 同色描边」。
 * ────────────────────────────────────────────────────────────────────
 */
interface RuntimeDebt {
  page: string;
  fg: string;
  bg: string;
  fs: string;
  max: number;
  reason: string;
}

const KNOWN_RUNTIME_DEBT: RuntimeDebt[] = [];

/**
 * 存量基线文件（自动维护）。
 * ============================================================================
 * `KNOWN_RUNTIME_DEBT` 适合登记"我逐条判断过、写了理由"的债务；
 * 但当一次性引入大量存量页（本轮从 12 页扩到 35 页）时，逐条誊抄 26 类
 * 既费时又容易抄错 —— 而**抄错的方向恰恰是危险的**（抄少了会把真问题当存量放过去）。
 *
 * 所以这里用一个基线文件：键是 `${页面}|${前景}|${背景}|${字号}`，值是允许的最大处数。
 *   · 命中且 ≤ 基线 → 记为存量，不阻断
 *   · 未命中，或超出基线 → **阻断**
 *   · 基线里某个键**消失了** → 只提示（说明修好了），提示更新基线把棘轮收紧
 *
 * 更新基线：`A11Y_UPDATE_BASELINE=1 npx playwright test a11y`（会重写整个文件）。
 * 收紧基线应当在**确认修复生效之后**做，而不是为了让它变绿。
 */
/**
 * 基线文件路径。**相对本文件所在目录**（`e2e/a11y/`），不要写成 `"a11y/xxx.json"` ——
 * 那样会拼成 `e2e/a11y/a11y/xxx.json`，目录不存在会让写基线静默失败（踩过）。
 */
const DEBT_BASELINE_PATH = "runtime-debt-baseline.json";

interface DebtBaseline {
  updatedAt: string;
  note: string;
  /** key = `${页面}|${前景}|${背景}|${字号}`，value = 允许的最大处数 */
  entries: Record<string, number>;
}

function loadDebtBaseline(): DebtBaseline | null {
  try {
    const raw = readFileSync(resolve(__dirname, DEBT_BASELINE_PATH), "utf8");
    return JSON.parse(raw) as DebtBaseline;
  } catch {
    return null;
  }
}

function groupKey(page: string, fg: string, bg: string, fs: string): string {
  return `${page}|${fg}|${bg}|${fs}`;
}

/** 汇总当前失败为 (页面, 色对) → 处数，供写基线用。 */
function summarize(failures: Failure[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const f of failures) {
    const page = (f.text.match(/^\[([^\]]+)\]/) || [, "?"])[1] as string;
    const key = groupKey(page, f.color, f.background, f.fontSize);
    out[key] = (out[key] || 0) + 1;
  }
  return out;
}
/**
 * 用例划分：**整个闸就是一个 test，只登录一次。**
 *
 * 为什么不用 Playwright 惯常的"一页一 test"：本仓库的登录限流是 **5 次/分钟/IP**。
 * 实测把闸展开成 30+ 个用例后，跑到后半段会出现"login() 报告成功、页面却仍被重定向到
 * /login"，于是要么**静默审计登录页并报绿**（最危险），要么整批失败。
 * 收敛成一次登录后，这一类问题从根上消失，总耗时也更短。
 *
 * 代价：一处页面崩溃会中断整轮。所以**先收集完所有页面的失败，最后断言一次**，
 * 每条失败都带 `[页面名]` 前缀，报告仍可直接定位。
 */
test.describe("运行时对比度与主题适配闸", () => {
  const admin = TEST_USERS.admin;

  test("全部页面 · 明暗双主题 · 含交互态与浅色表面", async ({ page, baseURL }) => {
    // 覆盖面扩到 35 个目标 × 2 主题 = 70 次页面访问，每次都要等客户端鉴权判定（2s）
    // 与内容稳定，实测约 10–12 分钟。留出充足余量，避免把"环境慢"误报成"有缺陷"
    // （曾经因为 20 分钟的硬超时，把一次 2.4 分钟就能跑完的检查变成失败）。
    test.setTimeout(40 * 60 * 1000);
    const base = baseURL || "http://localhost:3003";
    await login(page, admin.username, admin.password);

    const ids = await discoverIds(page, base);
    const targets = [...STATIC_PAGES];
    // 详情类页面：ID 在运行时通过 API 发现。
    // 不这样做的话，这类页面根本进不了覆盖面 —— 而本闸抓到的第一个真实缺陷就在工单详情上。
    if (ids.caseId) targets.push({ label: "工单详情", path: `/cases/${ids.caseId}` });
    if (ids.playbookId) {
      targets.push({ label: "剧本详情", path: `/playbooks/${ids.playbookId}` });
      targets.push({
        label: "剧本定义详情",
        path: `/playbooks/definitions/${ids.playbookId}`,
      });
      targets.push({
        label: "剧本定义编辑",
        path: `/playbooks/definitions/${ids.playbookId}/edit`,
      });
    }

    const failures: Failure[] = [];
    const lightSurfaces: Array<{
      tag: string;
      className: string;
      background: string;
      size: string;
    }> = [];
    const skipped: string[] = [];

    // ---------- 一、静止态：明暗双主题（深色轮顺带采浅色表面，不重复访问） ----------
    for (const theme of THEMES) {
      await useTheme(page, theme);
      let count = 0;
      let skippedGradients = 0;
      for (const target of targets) {
        const result = await audit(page, base, target.label, target.path, admin, {
          collectSurfaces: theme === "dark",
        });
        count += result.failures.length;
        failures.push(...result.failures);
        lightSurfaces.push(...result.surfaces);
        skippedGradients += result.gradientSkipped;
      }
      console.log(
        `[静止态·${theme}] 审计 ${targets.length} 个页面，不达标 ${count} 处` +
          (skippedGradients
            ? `；另有 ${skippedGradients} 处因背景是渐变而无法判定，已跳过（不计入结论）`
            : "")
      );
    }

    // ---------- 二、交互后才出现的状态 ----------
    for (const probe of INTERACTION_PROBES) {
      await useTheme(page, probe.theme);

      let path = probe.path;
      if (path.includes("{playbookId}")) {
        if (!ids.playbookId) {
          skipped.push(`${probe.label}[${probe.theme}]：剧本数据为空`);
          continue;
        }
        path = path.replace("{playbookId}", ids.playbookId);
      }

      await gotoAuthed(page, base, path, admin);
      await page.mouse.move(1, 1);

      const ready = page.getByRole("button", { name: probe.ready }).filter({ visible: true });
      try {
        await ready.first().waitFor({ state: "visible", timeout: 20000 });
      } catch {
        skipped.push(`${probe.label}[${probe.theme}]：未渲染出就绪标志 ${probe.ready}`);
        continue;
      }

      await sweep(page);

      // filter({visible:true}) 是必须的：同文案的按钮在侧栏/移动抽屉里有隐藏副本。
      const target = page
        .getByRole("button", { name: probe.click })
        .filter({ visible: true })
        .first();
      try {
        await target.waitFor({ state: "visible", timeout: 15000 });
      } catch {
        skipped.push(`${probe.label}[${probe.theme}]：找不到可见的 ${probe.click}`);
        continue;
      }

      await target.click();
      await waitForStable(page);

      const probeResult = await page.evaluate(collectFailures);
      for (const item of probeResult.failures) {
        item.text = `[${probe.label}·${probe.theme}] ${item.text}`;
      }
      failures.push(...probeResult.failures);
    }

    if (skipped.length) console.log("跳过：" + skipped.join("；"));

    // ---------- 断言一：深色下的浅色表面（第三方组件未适配主题） ----------
    const surfaceReport =
      lightSurfaces.length === 0
        ? "无未适配主题的浅色表面"
        : `${lightSurfaces.length} 处大面积浅色表面出现在深色主题下\n` +
          lightSurfaces
            .map((s) => `  · <${s.tag}> ${s.size} ${s.background}\n      ${s.className}`)
            .join("\n") +
          `\n\n多为第三方组件未做主题适配。优先在 app/globals.css 用语义 token 覆盖写死的颜色。`;
    console.log("浅色表面探针：" + surfaceReport.split("\n")[0]);
    expect.soft(lightSurfaces, surfaceReport).toEqual([]);

    // ---------- 断言二：对比度（含债务棘轮 + 基线） ----------
    const baseline = loadDebtBaseline();

    // 重写基线：只在显式要求时执行，避免"顺手让它变绿"
    if (process.env.A11Y_UPDATE_BASELINE === "1") {
      const entries = summarize(failures);
      const payload: DebtBaseline = {
        updatedAt: new Date().toISOString().slice(0, 10),
        note:
          "运行时对比度存量基线。key = 页面|前景|背景|字号，value = 允许的最大处数。" +
          "该数字只应下降。更新前请确认修复已生效（A11Y_UPDATE_BASELINE=1 npx playwright test a11y）。",
        entries: Object.fromEntries(Object.entries(entries).sort(([a], [b]) => a.localeCompare(b))),
      };
      writeFileSync(
        resolve(__dirname, DEBT_BASELINE_PATH),
        JSON.stringify(payload, null, 2) + "\n",
        "utf8"
      );
      console.log(`已重写基线：${Object.keys(entries).length} 类 / ${failures.length} 处`);
    }

    const { unexpected, tolerated } = applyDebtRatchet(failures, baseline);

    if (tolerated.length) {
      const total = tolerated.reduce((a, t) => a + t.count, 0);
      console.log(
        `已知债务（不阻断）：${total} 处 / ${tolerated.length} 类，涉及页面 ` +
          `${[...new Set(tolerated.map((t) => t.page))].join("、")}`
      );
      for (const t of tolerated) {
        console.log(
          `  ×${t.count}/${t.max} ${t.sample.ratio}:1  ${t.fg} on ${t.bg} @ ${t.fs}  [${t.page}]`
        );
      }
    }

    // 基线里"已经不再出现"的键 = 修好了，提示收紧棘轮（不是失败，但是行动信号）
    if (baseline) {
      const current = summarize(failures);
      const fixed = Object.keys(baseline.entries).filter((k) => !current[k]);
      if (fixed.length) {
        console.log(
          `基线中有 ${fixed.length} 类已不再出现（说明修好了），建议更新基线把棘轮收紧：\n` +
            fixed.map((k) => `  ${k}`).join("\n")
        );
      }
    }

    expect(unexpected, formatFailures("运行时对比度（新增/超出债务上限）", unexpected)).toEqual([]);
  });
});

interface DebtGroup {
  page: string;
  fg: string;
  bg: string;
  fs: string;
  count: number;
  sample: Failure;
  max: number;
  reason: string;
}

/**
 * 债务棘轮：把失败按 (页面, 前景, 背景, 字号) 这一"色对"分组，与 KNOWN_RUNTIME_DEBT 比对。
 *
 * - 命中且数量 ≤ max → 记为已知债务，**不阻断**（存量允许存在）
 * - 未命中，或数量 > max → 归入 unexpected，**阻断构建**（新增的问题不许溜过去）
 *
 * 这样闸在"存量还没清完"的情况下依然可用，同时把存量钉住只降不升。
 */
function applyDebtRatchet(
  failures: Failure[],
  baseline: DebtBaseline | null
): { unexpected: Failure[]; tolerated: DebtGroup[] } {
  const groups = new Map<
    string,
    { items: Failure[]; page: string; fg: string; bg: string; fs: string }
  >();
  for (const f of failures) {
    const page = (f.text.match(/^\[([^\]]+)\]/) || [, "?"])[1] as string;
    const key = groupKey(page, f.color, f.background, f.fontSize);
    const g = groups.get(key);
    if (g) g.items.push(f);
    else groups.set(key, { items: [f], page, fg: f.color, bg: f.background, fs: f.fontSize });
  }

  const unexpected: Failure[] = [];
  const tolerated: DebtGroup[] = [];

  for (const [key, g] of groups) {
    // 上限来源：显式登记的 KNOWN_RUNTIME_DEBT 优先，其次基线文件
    const declared = KNOWN_RUNTIME_DEBT.find(
      (d) => d.page === g.page && d.fg === g.fg && d.bg === g.bg && d.fs === g.fs
    );
    const max = declared ? declared.max : (baseline?.entries[key] ?? 0);
    const reason = declared
      ? declared.reason
      : max > 0
        ? "基线存量（扩面时一次性引入，待逐类清理）"
        : "";

    if (max > 0 && g.items.length <= max) {
      tolerated.push({
        page: g.page,
        fg: g.fg,
        bg: g.bg,
        fs: g.fs,
        count: g.items.length,
        sample: g.items[0],
        max,
        reason,
      });
    } else {
      unexpected.push(...g.items);
    }
  }

  tolerated.sort((a, b) => b.count - a.count);
  return { unexpected, tolerated };
}

function formatFailures(scope: string, failures: Failure[]): string {
  if (failures.length === 0) return `${scope}：无低于 AA 的文本`;

  // 同类合并：同一 (页面, 前景, 背景, 字号) 只列一条 + 次数，
  // 否则几十类并排会刷屏，反而看不清"到底要修哪几个色"。
  const byKind = new Map<string, { count: number; sample: Failure }>();
  for (const f of failures) {
    const page = (f.text.match(/^\[([^\]]+)\]/) || [, "?"])[1] as string;
    const key = `${page}|${f.color}|${f.background}|${f.fontSize}|${f.required}`;
    const hit = byKind.get(key);
    if (hit) hit.count++;
    else byKind.set(key, { count: 1, sample: f });
  }

  const lines = [...byKind.entries()].map(([, { count, sample }]) => {
    return (
      `  · ×${count} ${sample.ratio}:1（要求 ${sample.required}:1）\n` +
      `      color ${sample.color} on ${sample.background} @ ${sample.fontSize}\n` +
      `      例："${sample.text}"\n` +
      `      class: ${sample.className}`
    );
  });

  return (
    `${scope}：${failures.length} 处文本低于 WCAG AA（合并为 ${byKind.size} 类）\n` +
    lines.join("\n") +
    `\n\n若确属"存量债务"，按 (页面, 前景, 背景, 字号) 加进 KNOWN_RUNTIME_DEBT 并写明根因与上限；` +
    `\n不要去放宽全局阈值，也不要把不同形状的问题混进同一条。`
  );
}
