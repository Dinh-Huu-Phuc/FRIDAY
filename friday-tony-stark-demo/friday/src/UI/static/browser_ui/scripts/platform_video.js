(() => {
  "use strict";

  const host = window.location.hostname.toLowerCase();
  const isYouTube =
    (host === "youtube.com" || host === "www.youtube.com") &&
    window.location.pathname === "/results";
  const isTikTok =
    (host === "tiktok.com" || host === "www.tiktok.com") &&
    window.location.pathname.startsWith("/search");
  if (!isYouTube && !isTikTok) {
    return;
  }

  const requestedRank = Number(
    new URLSearchParams(window.location.search).get("friday_play")
  );
  if (!Number.isInteger(requestedRank) || requestedRank < 1 || requestedRank > 3) {
    return;
  }

  const selector = isYouTube
    ? "ytd-video-renderer a#thumbnail[href*='/watch'], " +
      "ytd-rich-item-renderer a#thumbnail[href*='/watch']"
    : "main a[href*='/video/']";
  let completed = false;
  let observer = null;

  function uniqueResults() {
    const seen = new Set();
    return Array.from(document.querySelectorAll(selector)).filter((item) => {
      const href = item.href || item.getAttribute("href") || "";
      if (!href || seen.has(href)) {
        return false;
      }
      seen.add(href);
      return true;
    });
  }

  function selectVideo() {
    if (completed) {
      return;
    }
    const firstThree = uniqueResults().slice(0, 3);
    const target = firstThree[requestedRank - 1];
    if (!target) {
      return;
    }
    completed = true;
    if (observer) {
      observer.disconnect();
    }
    target.click();
  }

  observer = new MutationObserver(selectVideo);
  observer.observe(document.documentElement, { childList: true, subtree: true });
  window.setTimeout(selectVideo, 250);
  window.setTimeout(() => observer?.disconnect(), 20000);
})();
