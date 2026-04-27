#!/usr/bin/env node
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import sharp from "sharp";
import pngToIco from "png-to-ico";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(__dirname, "..");

const BRAND_DIR = resolve(projectRoot, "public/brand");
const PUBLIC_DIR = resolve(projectRoot, "public");
const APP_DIR = resolve(projectRoot, "src/app");

async function ensureDir(path) {
  await mkdir(path, { recursive: true });
}

async function svgToPng(svgPath, outPath, size) {
  const svg = await readFile(svgPath);
  await ensureDir(dirname(outPath));
  await sharp(svg, { density: 384 })
    .resize(size, size, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png({ compressionLevel: 9 })
    .toFile(outPath);
  console.log(`  ✓ ${outPath} (${size}×${size})`);
}

async function svgToMaskPng(svgPath, outPath, size) {
  // Maskable icons need a solid background and 80% safe zone (per W3C spec).
  // We render the SVG inside a centered safe area on a #1574d2 background.
  const svg = await readFile(svgPath);
  await ensureDir(dirname(outPath));
  const safe = Math.round(size * 0.8);
  const inner = await sharp(svg, { density: 384 })
    .resize(safe, safe, { fit: "contain", background: { r: 0, g: 0, b: 0, alpha: 0 } })
    .png()
    .toBuffer();
  await sharp({
    create: {
      width: size,
      height: size,
      channels: 4,
      background: { r: 21, g: 116, b: 210, alpha: 1 },
    },
  })
    .composite([{ input: inner, gravity: "center" }])
    .png({ compressionLevel: 9 })
    .toFile(outPath);
  console.log(`  ✓ ${outPath} (${size}×${size}, maskable)`);
}

async function buildFavicon() {
  console.log("\nFavicon (.ico)");
  const tmp32 = resolve(BRAND_DIR, "_favicon-32.png");
  const tmp16 = resolve(BRAND_DIR, "_favicon-16.png");
  await svgToPng(resolve(BRAND_DIR, "favicon.svg"), tmp32, 32);
  await svgToPng(resolve(BRAND_DIR, "favicon.svg"), tmp16, 16);
  const ico = await pngToIco([tmp32, tmp16]);
  const icoPath = resolve(APP_DIR, "favicon.ico");
  await writeFile(icoPath, ico);
  console.log(`  ✓ ${icoPath}`);
  // Cleanup tmp pngs
  await Promise.all([
    sharp(tmp32).toFile(tmp32 + ".bak").then(() => readFile(tmp32)).catch(() => {}),
  ]);
  // Just delete tmp files
  const { unlink } = await import("node:fs/promises");
  await Promise.allSettled([unlink(tmp32), unlink(tmp16), unlink(tmp32 + ".bak")]);
}

async function buildAppIcons() {
  console.log("\nApp icons (PWA)");
  const master = resolve(BRAND_DIR, "app-icon-master.svg");
  await svgToPng(master, resolve(BRAND_DIR, "icon-192.png"), 192);
  await svgToPng(master, resolve(BRAND_DIR, "icon-512.png"), 512);
  await svgToMaskPng(master, resolve(BRAND_DIR, "icon-mask.png"), 512);
}

async function buildAppleIcon() {
  console.log("\nApple touch icon");
  await svgToPng(
    resolve(BRAND_DIR, "app-icon-master.svg"),
    resolve(APP_DIR, "apple-icon.png"),
    180,
  );
}

async function buildLegacyPublicIcons() {
  // Mirror to public/ root so existing absolute paths in metadata still resolve
  // until consumers migrate to /brand/icon-*.png.
  console.log("\nLegacy public/ icons (compat)");
  const master = resolve(BRAND_DIR, "app-icon-master.svg");
  await svgToPng(master, resolve(PUBLIC_DIR, "icon-192.png"), 192);
  await svgToPng(master, resolve(PUBLIC_DIR, "icon-512.png"), 512);
  await svgToPng(master, resolve(PUBLIC_DIR, "apple-touch-icon.png"), 180);
}

async function copyAppIconSvg() {
  console.log("\nNext App Router icon.svg");
  const src = await readFile(resolve(BRAND_DIR, "favicon.svg"));
  const out = resolve(APP_DIR, "icon.svg");
  await writeFile(out, src);
  console.log(`  ✓ ${out}`);
}

async function main() {
  console.log("Building brand icons from SVG masters in public/brand/");
  await buildFavicon();
  await copyAppIconSvg();
  await buildAppIcons();
  await buildAppleIcon();
  await buildLegacyPublicIcons();
  console.log("\nDone.");
}

main().catch((err) => {
  console.error("Icon build failed:", err);
  process.exit(1);
});
