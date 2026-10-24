// Enforces docs/design-system.md and docs/copy.md: sizes and colours live only in
// custom-property declarations (the token blocks), and visible strings avoid banned words.
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const siteDirectory = join(dirname(fileURLToPath(import.meta.url)), "..", "site");

function siteFiles(extension) {
  return readdirSync(siteDirectory)
    .filter((fileName) => fileName.endsWith(extension))
    .map((fileName) => ({ fileName, text: readFileSync(join(siteDirectory, fileName), "utf8") }));
}

function stripCssComments(cssText) {
  return cssText.replace(/\/\*[\s\S]*?\*\//g, "");
}

// Every "property: value" pair inside a rule body. @media preludes and selectors are not
// declarations, so breakpoints never show up here.
function cssDeclarations(cssText) {
  const declarations = [];
  const bodyPattern = /\{([^{}]*)\}/g;
  for (const bodyMatch of cssText.matchAll(bodyPattern)) {
    for (const part of bodyMatch[1].split(";")) {
      const colonIndex = part.indexOf(":");
      if (colonIndex === -1) continue;
      declarations.push({ property: part.slice(0, colonIndex).trim(), value: part.slice(colonIndex + 1).trim() });
    }
  }
  return declarations;
}

// 1px borders and the 2px focus outline are the only raw lengths the spec allows.
const ALLOWED_RAW_LENGTHS = new Set(["0px", "1px", "2px"]);
const LENGTH_PATTERN = /-?\d*\.?\d+(px|rem)\b/g;
const COLOUR_PATTERN = /#[0-9a-f]{3,8}\b|\b(rgb|rgba|hsl|hsla)\(/i;

test("stylesheets keep sizes and colours in tokens", () => {
  const problems = [];
  for (const { fileName, text } of siteFiles(".css")) {
    for (const { property, value } of cssDeclarations(stripCssComments(text))) {
      if (property.startsWith("--")) continue;
      for (const [length] of value.matchAll(LENGTH_PATTERN)) {
        if (!ALLOWED_RAW_LENGTHS.has(length)) problems.push(`${fileName}: ${property}: ${value}`);
      }
      if (COLOUR_PATTERN.test(value)) problems.push(`${fileName}: ${property}: ${value}`);
    }
  }
  assert.deepEqual(problems, [], `Raw sizes or colours outside tokens:\n${problems.join("\n")}`);
});

const BANNED_PHRASES = ["lead PI", "matching grants", "runway", "localStorage", "fingerprint", "invalid", "please", "Default view"];

function visibleHtmlStrings(htmlText) {
  const withoutCode = htmlText
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "");
  const attributeValues = [...withoutCode.matchAll(/\b(placeholder|title|aria-label|alt)="([^"]*)"/g)].map((match) => match[2]);
  const textNodes = withoutCode.split(/<[^>]*>/).map((text) => text.trim()).filter(Boolean);
  return [...attributeValues, ...textNodes];
}

// String literals in scripts, minus ${...} expressions. Code-only strings (selectors,
// storage keys) are included too, so a banned word must not appear in those either.
function scriptStringLiterals(scriptText) {
  const withoutComments = scriptText.replace(/\/\*[\s\S]*?\*\//g, "").replace(/(^|[^:\\])\/\/.*$/gm, "$1");
  const literalPattern = /"(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`/g;
  return [...withoutComments.matchAll(literalPattern)].map((match) => match[0].slice(1, -1).replace(/\$\{[^}]*\}/g, " "));
}

function findBannedCopy(fileName, strings) {
  const problems = [];
  for (const text of strings) {
    for (const phrase of BANNED_PHRASES) {
      if (text.toLowerCase().includes(phrase.toLowerCase())) problems.push(`${fileName}: "${phrase}" in "${text}"`);
    }
    if (/[A-Za-z]!(\s|$)/.test(text)) problems.push(`${fileName}: exclamation mark in "${text}"`);
  }
  return problems;
}

test("visible strings avoid banned words", () => {
  const problems = [];
  for (const { fileName, text } of siteFiles(".html")) problems.push(...findBannedCopy(fileName, visibleHtmlStrings(text)));
  for (const { fileName, text } of siteFiles(".js")) {
    if (fileName === "data.js") continue;
    // A single lowercase word such as "runway" is a code key (sort name, storage key), not copy.
    const codeKeyPattern = /^[a-z][a-zA-Z0-9_-]*$/;
    const literals = scriptStringLiterals(text).filter((literal) => !codeKeyPattern.test(literal));
    problems.push(...findBannedCopy(fileName, literals));
  }
  assert.deepEqual(problems, [], `Banned copy:\n${problems.join("\n")}`);
});
