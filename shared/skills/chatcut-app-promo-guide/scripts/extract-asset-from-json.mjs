#!/usr/bin/env node

import * as fs from "node:fs";
import * as path from "node:path";

const USAGE_HINT =
  "Usage: node .claude/skills/app-promo-guide/scripts/extract-asset-from-json.mjs <json-file> <output-dir> <output-basename> <field-path> [field-path ...]";

function extensionForMime(mime) {
  return (
    {
      "image/gif": "gif",
      "image/jpeg": "jpg",
      "image/png": "png",
      "image/svg+xml": "svg",
      "image/webp": "webp",
      "video/mp4": "mp4",
      "video/webm": "webm",
    }[String(mime).toLowerCase()] || "bin"
  );
}

function parseDataUri(raw) {
  if (!raw.startsWith("data:")) throw new Error("Asset is not a data URI");
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
  return { buffer, mime };
}

function getByPath(value, fieldPath) {
  return fieldPath.split(".").reduce((current, segment) => {
    if (current == null) return undefined;
    return current[segment];
  }, value);
}

function firstStringAtPaths(value, fieldPaths) {
  for (const fieldPath of fieldPaths) {
    const candidate = getByPath(value, fieldPath);
    if (typeof candidate === "string" && candidate.length > 0) {
      return { fieldPath, value: candidate };
    }
  }
  return null;
}

async function saveUrlAsset(assetUrl, outputDir, outputBasename) {
  const response = await fetch(assetUrl);
  if (!response.ok) {
    throw new Error(`Failed to fetch asset URL: HTTP ${response.status}`);
  }

  const mime = response.headers.get("content-type")?.split(";")[0] || "";
  const buffer = Buffer.from(await response.arrayBuffer());
  const outputPath = path.join(
    outputDir,
    `${outputBasename}.${extensionForMime(mime)}`,
  );
  fs.writeFileSync(outputPath, buffer);
  console.log(
    `Saved URL asset -> ${outputPath} (${buffer.length} bytes, ${mime || "unknown mime"})`,
  );
}

function saveDataUriAsset(assetValue, outputDir, outputBasename) {
  const dataUriPath = path.join(outputDir, `${outputBasename}.datauri`);
  fs.writeFileSync(dataUriPath, assetValue);

  const { buffer, mime } = parseDataUri(assetValue);
  const outputPath = path.join(
    outputDir,
    `${outputBasename}.${extensionForMime(mime)}`,
  );
  fs.writeFileSync(outputPath, buffer);
  console.log(
    `Saved data URI asset -> ${outputPath} (${buffer.length} bytes, ${mime})`,
  );
}

async function main() {
  const [inputPath, outputDir, outputBasename, ...fieldPaths] =
    process.argv.slice(2);
  if (!inputPath || !outputDir || !outputBasename || fieldPaths.length === 0) {
    throw new Error(`Missing required arguments. ${USAGE_HINT}`);
  }

  const parsed = JSON.parse(fs.readFileSync(inputPath, "utf8"));
  const match = firstStringAtPaths(parsed, fieldPaths);
  if (!match) {
    throw new Error(`No string asset found at paths: ${fieldPaths.join(", ")}`);
  }

  fs.mkdirSync(outputDir, { recursive: true });
  if (match.value.startsWith("data:")) {
    saveDataUriAsset(match.value, outputDir, outputBasename);
    return;
  }
  if (/^https?:\/\//i.test(match.value)) {
    await saveUrlAsset(match.value, outputDir, outputBasename);
    return;
  }
  throw new Error(
    `Unsupported asset reference at ${match.fieldPath}: expected data URI or http(s) URL`,
  );
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});
