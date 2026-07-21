// ==UserScript==
// @name         Friday Agent Code Enhancer for LiveKit Playground
// @namespace    https://github.com/livekit/agents-playground
// @version      1.2.0
// @description  Format agent source code output with copy button on agents-playground.livekit.io
// @author       Friday Team
// @match        https://agents-playground.livekit.io/*
// @run-at       document-idle
// @grant        none
// ==/UserScript==

(function () {
  "use strict";

  const ENHANCED_ATTR = "data-friday-enhanced";
  const SOURCE_HASH_ATTR = "data-friday-source-hash";
  const ENHANCED_CLASS = "friday-enhanced-content";
  const DEFAULT_LANG = "text";
  const MAX_TEXT_LENGTH = 30000;
  const FORCE_BTN_ID = "friday-enhancer-force-btn";

  const CODE_FENCE_RE =
    /(?:^|\n)\s*["'“”‘’]?`{3,}\s*([a-zA-Z0-9_+#.-]*)\s*\n([\s\S]*?)(?:\n\s*`{3,}\s*["'“”‘’]?)(?=\s*(?:\n|$))/g;

  function injectStyles() {
    const style = document.createElement("style");
    style.textContent = `
.${ENHANCED_CLASS} { margin-top: 4px; }
.friday-rendered-text { white-space: pre-wrap; line-height: 1.5; }
.friday-code-block {
  margin: 10px 0;
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 12px;
  overflow: hidden;
  background: #0b1220;
}
.friday-code-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(90deg, #0f172a 0%, #111827 100%);
  border-bottom: 1px solid rgba(255,255,255,0.14);
  padding: 8px 10px;
  font-size: 12px;
}
.friday-code-lang {
  color: #7dd3fc;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.friday-copy-btn {
  border: 1px solid rgba(125,211,252,0.3);
  background: rgba(2,132,199,0.12);
  color: #bae6fd;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1;
  padding: 6px 9px;
  cursor: pointer;
}
.friday-copy-btn:hover { background: rgba(2,132,199,0.24); }
.friday-code-pre {
  margin: 0;
  padding: 12px;
  overflow-x: auto;
  font-size: 13px;
  line-height: 1.5;
  color: #dbeafe;
}
.friday-code-pre code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, "Liberation Mono", monospace;
}
.friday-copy-toast {
  position: fixed;
  right: 16px;
  bottom: 16px;
  background: rgba(15,23,42,0.96);
  color: #e2e8f0;
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  z-index: 999999;
  pointer-events: none;
}
#${FORCE_BTN_ID} {
  position: fixed;
  right: 16px;
  top: 72px;
  z-index: 999998;
  border: 1px solid rgba(125,211,252,0.34);
  background: rgba(2,132,199,0.18);
  color: #bae6fd;
  border-radius: 999px;
  padding: 6px 10px;
  font-size: 12px;
  cursor: pointer;
}
#${FORCE_BTN_ID}:hover {
  background: rgba(2,132,199,0.28);
}
`;
    document.head.appendChild(style);
  }

  function showToast(message) {
    const node = document.createElement("div");
    node.className = "friday-copy-toast";
    node.textContent = message;
    document.body.appendChild(node);
    window.setTimeout(() => node.remove(), 1300);
  }

  async function copyText(text) {
    try {
      await navigator.clipboard.writeText(text);
      showToast("Copied");
    } catch {
      showToast("Copy failed");
    }
  }

  function normalizeText(text) {
    let out = String(text || "");
    out = out.replace(/\r\n/g, "\n");
    out = out.replace(/[“”]/g, '"').replace(/[‘’]/g, "'");
    out = out.replace(/^"\s*`{3,}/gm, "```");
    out = out.replace(/`{3,}\s*"$/gm, "```");
    return out;
  }

  function escapeHtml(text) {
    return String(text)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  }

  function inferLanguage(code) {
    const src = String(code || "");
    if (/#include\s*<.*?>/.test(src) || /\bstd::/.test(src)) return "cpp";
    if (/\bdef\s+\w+\s*\(/.test(src) || /\bimport\s+\w+/.test(src)) return "python";
    if (/\bfunction\s+\w+\s*\(/.test(src) || /\bconsole\.log\(/.test(src)) return "javascript";
    if (/<[a-z][\s\S]*>/.test(src) && /<\/[a-z]+>/.test(src)) return "html";
    if (/^\s*(SELECT|INSERT|UPDATE|DELETE)\b/i.test(src)) return "sql";
    return DEFAULT_LANG;
  }

  function looksLikeCode(text) {
    const src = String(text || "");
    const lines = src.split("\n").map((x) => x.trim()).filter(Boolean);
    if (lines.length < 4) return false;
    let score = 0;
    for (const line of lines) {
      if (/^\s*#include\b/.test(line)) score += 3;
      if (/^\s*(def|class|if|for|while|return|function|const|let|var|int|float|double)\b/.test(line)) score += 2;
      if (/[{};]/.test(line)) score += 1;
      if (/=\s*.+/.test(line)) score += 1;
    }
    return score >= 6;
  }

  function splitSegments(rawText) {
    const text = normalizeText(rawText);
    const segments = [];
    let cursor = 0;
    let match;
    CODE_FENCE_RE.lastIndex = 0;

    while ((match = CODE_FENCE_RE.exec(text)) !== null) {
      const full = match[0];
      const language = (match[1] || "").trim().toLowerCase() || DEFAULT_LANG;
      const code = String(match[2] || "").replace(/\n+$/, "");
      const start = match.index;
      const end = start + full.length;

      if (start > cursor) {
        const before = text.slice(cursor, start);
        if (before.trim()) {
          segments.push({ type: "text", value: before });
        }
      }
      segments.push({ type: "code", language, value: code });
      cursor = end;
    }

    if (cursor < text.length) {
      const tail = text.slice(cursor);
      if (tail.trim()) {
        segments.push({ type: "text", value: tail });
      }
    }

    if (!segments.length && looksLikeCode(text)) {
      segments.push({
        type: "code",
        language: inferLanguage(text),
        value: text.trim(),
      });
    }
    return segments;
  }

  function createCodeBlock(language, code) {
    const wrapper = document.createElement("div");
    wrapper.className = "friday-code-block";

    const toolbar = document.createElement("div");
    toolbar.className = "friday-code-toolbar";

    const langNode = document.createElement("span");
    langNode.className = "friday-code-lang";
    langNode.textContent = language;

    const copyBtn = document.createElement("button");
    copyBtn.type = "button";
    copyBtn.className = "friday-copy-btn";
    copyBtn.setAttribute("aria-label", "Copy code");
    copyBtn.textContent = "📋 Copy";
    copyBtn.addEventListener("click", () => copyText(code));

    toolbar.appendChild(langNode);
    toolbar.appendChild(copyBtn);

    const pre = document.createElement("pre");
    pre.className = "friday-code-pre";
    const codeNode = document.createElement("code");
    codeNode.textContent = code;
    pre.appendChild(codeNode);

    wrapper.appendChild(toolbar);
    wrapper.appendChild(pre);
    return wrapper;
  }

  function createEnhancedContent(text) {
    const segments = splitSegments(text);
    if (!segments.length) return null;

    const root = document.createElement("div");
    root.className = ENHANCED_CLASS;

    for (const seg of segments) {
      if (seg.type === "text") {
        const node = document.createElement("div");
        node.className = "friday-rendered-text";
        node.innerHTML = escapeHtml(seg.value).replace(/\n/g, "<br>");
        root.appendChild(node);
      } else {
        root.appendChild(createCodeBlock(seg.language, seg.value));
      }
    }
    return root;
  }

  function textHash(text) {
    let hash = 0;
    const str = String(text || "");
    for (let i = 0; i < str.length; i += 1) {
      hash = (hash * 31 + str.charCodeAt(i)) >>> 0;
    }
    return String(hash);
  }

  function elementText(el) {
    return String(el.textContent || "").trim();
  }

  function hasPossibleCode(text) {
    return text.includes("```") || looksLikeCode(text);
  }

  function isEligible(el) {
    if (!(el instanceof HTMLElement)) return false;
    if (el.closest(`.${ENHANCED_CLASS}`)) return false;
    if (el.closest("pre, code")) return false;

    const txt = elementText(el);
    if (!txt || txt.length > MAX_TEXT_LENGTH) return false;
    return hasPossibleCode(txt);
  }

  function enhanceElement(el) {
    const src = elementText(el);
    const hash = textHash(src);
    const oldHash = el.getAttribute(SOURCE_HASH_ATTR) || "";

    if (el.getAttribute(ENHANCED_ATTR) === "1" && hash === oldHash) {
      return;
    }

    const enhanced = createEnhancedContent(src);
    if (!enhanced) return;

    el.innerHTML = "";
    el.appendChild(enhanced);
    el.setAttribute(ENHANCED_ATTR, "1");
    el.setAttribute(SOURCE_HASH_ATTR, hash);
  }

  function runEnhancer() {
    const nodes = document.querySelectorAll("div, p, span, li, article, section");
    nodes.forEach((node) => {
      if (isEligible(node)) {
        enhanceElement(node);
      }
    });
  }

  function installObserver() {
    const observer = new MutationObserver(() => runEnhancer());
    observer.observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true,
    });
  }

  function installForceButton() {
    if (document.getElementById(FORCE_BTN_ID)) return;
    const button = document.createElement("button");
    button.id = FORCE_BTN_ID;
    button.textContent = "✨ Format Code";
    button.addEventListener("click", () => {
      runEnhancer();
      showToast("Code reformatted");
    });
    document.body.appendChild(button);
  }

  function bootstrap() {
    injectStyles();
    installForceButton();
    runEnhancer();
    installObserver();
    window.setInterval(runEnhancer, 1200);
    console.info("[FridayEnhancer] Ready");
  }

  try {
    bootstrap();
  } catch (error) {
    console.error("[FridayEnhancer] Fatal error:", error);
  }
})();
