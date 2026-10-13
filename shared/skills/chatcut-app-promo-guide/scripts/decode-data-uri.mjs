#!/usr/bin/env node

import * as fs from "node:fs";

const USAGE_HINT =
  "Usage: node .claude/skills/app-promo-guide/scripts/decode-data-uri.mjs <input-file> <output-file>";

function fail(message) {
  console.error(message);
  process.exitCode = 1;
}

function main() {
  const [inputPath, outputPath] = process.argv.slice(2);
  if (!inputPath || !outputPath) {
    throw new Error(`Missing input or output path. ${USAGE_HINT}`);
  }

  const raw = fs.readFileSync(inputPath, "utf8").trim();
  if (!raw.startsWith("data:")) throw new Error("Input is not a data URI");

  const commaIndex = raw.indexOf(",");
  if (commaIndex === -1) {
    throw new Error("Invalid data URI: missing comma separator");
  }

  const meta = raw.slice(5, commaIndex);
  const payload = raw.slice(commaIndex + 1);
  const metaParts = meta.split(";");
  const mime = metaParts[0] || "text/plain";
  const buffer = metaParts.includes("base64")
    ? Buffer.from(payload, "base64")
    : Buffer.from(decodeURIComponent(payload), "utf8");

  fs.writeFileSync(outputPath, buffer);
  console.log(`Decoded ${mime} -> ${outputPath} (${buffer.length} bytes)`);
}

try {
  main();
} catch (error) {
  fail(error instanceof Error ? error.message : String(error));
}
