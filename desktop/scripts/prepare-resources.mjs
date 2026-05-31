// 组装 Electron 打包所需资源：
//  resources/backend  <- PyInstaller 产物（含 tradeai-backend.exe）
//  resources/frontend <- Next standalone（server.js + .next + node_modules + static + public）
//
// 前置条件（本脚本不自动跑，需先各自构建）：
//  1. 后端：在 backend/ 下用 PyInstaller 打出 dist_desktop/tradeai-backend/
//  2. 前端：在 frontend/ 下 `npm run build`（next.config.mjs 已是 output: standalone）

import { existsSync, rmSync, mkdirSync, cpSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DESKTOP = join(__dirname, "..");
const ROOT = join(DESKTOP, "..");

const BACKEND_DIST = join(ROOT, "backend", "dist_desktop", "tradeai-backend");
const FRONTEND_STANDALONE = join(ROOT, "frontend", ".next", "standalone");
const FRONTEND_STATIC = join(ROOT, "frontend", ".next", "static");
const FRONTEND_PUBLIC = join(ROOT, "frontend", "public");

const RES = join(DESKTOP, "resources");
const RES_BACKEND = join(RES, "backend");
const RES_FRONTEND = join(RES, "frontend");

function fail(msg) {
  console.error(`\n[prepare-resources] 错误：${msg}\n`);
  process.exit(1);
}

function reset(dir) {
  if (existsSync(dir)) rmSync(dir, { recursive: true, force: true });
  mkdirSync(dir, { recursive: true });
}

// ---- 校验前置产物 ----
if (!existsSync(join(BACKEND_DIST, "tradeai-backend.exe"))) {
  fail(
    `未找到后端打包产物：${BACKEND_DIST}\n` +
      `请先在 backend/ 下运行：python -m PyInstaller desktop.spec --noconfirm --distpath dist_desktop --workpath build_desktop`,
  );
}
if (!existsSync(join(FRONTEND_STANDALONE, "server.js"))) {
  fail(
    `未找到前端 standalone 产物：${FRONTEND_STANDALONE}\n` +
      `请先在 frontend/ 下运行：npm run build`,
  );
}

// ---- 后端 ----
console.log("[prepare-resources] 拷贝后端…");
reset(RES_BACKEND);
cpSync(BACKEND_DIST, RES_BACKEND, { recursive: true });

// ---- 前端 ----
console.log("[prepare-resources] 拷贝前端 standalone…");
reset(RES_FRONTEND);
cpSync(FRONTEND_STANDALONE, RES_FRONTEND, { recursive: true });
// Next standalone 不含 static / public，需手动并入
cpSync(FRONTEND_STATIC, join(RES_FRONTEND, ".next", "static"), { recursive: true });
if (existsSync(FRONTEND_PUBLIC)) {
  cpSync(FRONTEND_PUBLIC, join(RES_FRONTEND, "public"), { recursive: true });
}

console.log("[prepare-resources] 完成。资源已就绪：");
console.log(`  - ${RES_BACKEND}`);
console.log(`  - ${RES_FRONTEND}`);
