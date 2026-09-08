import { readFileSync, writeFileSync } from "fs";
import { join } from "path";

const filePath = join(process.cwd(), "components", "Navigation.tsx");
let content = readFileSync(filePath, "utf-8");

// 1. 高度 56px (h-14)
content = content.replace("h-16", "h-14");

// 2. Logo: 移除渐变和 glow，使用纯色
content = content.replace(
  "bg-gradient-to-br from-soc-500 to-soc-700 flex items-center justify-center shadow-lg shadow-soc-500/25",
  "bg-primary-600 flex items-center justify-center"
);

// 3. 图标尺寸 20px
content = content.replace("w-4.5 h-4.5", "w-5 h-5");

// 4. 品牌文字颜色从 soc 改为 primary
content = content.replace(
  /text-soc-600 hover:text-soc-700 dark:text-soc-400 dark:hover:text-soc-300/g,
  "text-primary-600 hover:text-primary-700 dark:text-primary-400 dark:hover:text-primary-300"
);

// 5. 分割线 gray -> slate
content = content.replace(/bg-gray-200 dark:bg-gray-700/g, "bg-slate-200 dark:bg-slate-700");
content = content.replace(
  /border-gray-200 dark:border-gray-700/g,
  "border-slate-200 dark:border-slate-700"
);

// 6. 标题颜色 gray -> slate
content = content.replace(/text-gray-900 dark:text-white/g, "text-slate-900 dark:text-white");
content = content.replace(
  /text-gray-500 dark:text-gray-400/g,
  "text-slate-500 dark:text-slate-400"
);

// 7. API 状态背景
content = content.replace(/bg-gray-75 dark:bg-gray-700\/50/g, "bg-slate-50 dark:bg-slate-800");

// 8. API 状态文字
content = content.replace(
  /text-gray-600 dark:text-gray-300/g,
  "text-slate-600 dark:text-slate-300"
);

// 9. 主导航按钮颜色 gray -> slate (非 active 状态)
content = content.replace(
  /text-gray-700 dark:text-gray-300/g,
  "text-slate-700 dark:text-slate-300"
);
content = content.replace(
  /text-gray-400 dark:text-gray-500/g,
  "text-slate-400 dark:text-slate-500"
);
content = content.replace(/text-gray-400/g, "text-slate-400"); // 移动端 section headers

// 10. hover 背景
content = content.replace(
  /hover:bg-gray-100 dark:hover:bg-gray-700\/50/g,
  "hover:bg-slate-50 dark:hover:bg-slate-800"
);
content = content.replace(
  /hover:bg-gray-75 dark:hover:bg-gray-700\/50/g,
  "hover:bg-slate-50 dark:hover:bg-slate-800"
);

// 11. 移动端菜单背景
content = content.replace(/bg-gray-50 dark:bg-gray-700\/50/g, "bg-slate-50 dark:bg-slate-800");

// 12. 移动端文字颜色
content = content.replace(
  /text-gray-700 dark:text-gray-300/g,
  "text-slate-700 dark:text-slate-300"
);

// 13. 导航 active 状态: 文字改为 slate-900/white
content = content.replace(/text-soc-700 dark:text-soc-300/g, "text-slate-900 dark:text-white");

// 14. 下拉菜单背景 (shadow-elevated 保留，但背景改为纯白/纯暗)
content = content.replace(/bg-white dark:bg-gray-800/g, "bg-white dark:bg-slate-900");

// 15. 移动端菜单边框
content = content.replace(
  /border-gray-200 dark:border-gray-700/g,
  "border-slate-200 dark:border-slate-700"
);

// 16. 确保底部边框正确 (上面全局替换可能会影响这里)
// 前面已经替换了 border-gray-200 dark:border-gray-700 -> border-slate-200 dark:border-slate-700
// 但 nav 已经是 slate，需要确认没被覆盖

// 17. 移动端图标颜色
content = content.replace(
  /text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700\/50/g,
  "text-slate-500 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800"
);

// 18. 用户区域文字
content = content.replace(
  /text-gray-600 dark:text-gray-300 truncate/g,
  "text-slate-600 dark:text-slate-300 truncate"
);

// 19. active 背景使用更克制的 slate
content = content.replace(/bg-soc-50 dark:bg-soc-900\/30/g, "bg-slate-50 dark:bg-slate-800");

// 20. 角色标签：默认 gray -> slate
content = content.replace(
  /bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300/g,
  "bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300"
);

writeFileSync(filePath, content, "utf-8");
console.log("Navigation.tsx updated");
