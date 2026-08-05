(() => {
  "use strict";

  const allowedHosts = new Set(["google.com", "www.google.com"]);
  if (
    window.location.protocol !== "https:" ||
    !allowedHosts.has(window.location.hostname.toLowerCase()) ||
    window.location.pathname.replace(/\/+$/, "") !== "/search"
  ) {
    return;
  }

  const brandId = "friday-search-brand";
  const styleId = "friday-search-brand-style";
  const brandStyles = __FRIDAY_GOOGLE_BRAND_CSS__;
  const logoSelectors = [
    "a#logo",
    "#logo a",
    "a[aria-label='Google']",
    "a[aria-label*='Google'][href*='/webhp']",
    "a[href^='/webhp'] img[alt='Google']",
    "a[href*='google.com/webhp'] img[alt='Google']",
  ];
  let updateScheduled = false;

  function ensureStyles() {
    if (document.getElementById(styleId)) {
      return;
    }
    const style = document.createElement("style");
    style.id = styleId;
    style.textContent = brandStyles;
    (document.head || document.documentElement).appendChild(style);
  }

  function findLogoHost() {
    for (const selector of logoSelectors) {
      const candidate = document.querySelector(selector);
      if (!candidate) {
        continue;
      }
      if (candidate.matches("img, svg")) {
        return candidate.closest("a") || candidate.parentElement;
      }
      return candidate;
    }
    return null;
  }

  function applyFridayBrand() {
    ensureStyles();
    const host = findLogoHost();
    if (!host) {
      return;
    }

    let brand = document.getElementById(brandId);
    if (brand && brand.parentElement !== host) {
      brand.remove();
      brand = null;
    }
    if (!brand) {
      brand = document.createElement("span");
      brand.id = brandId;
      brand.textContent = "FRIDAY";
      brand.setAttribute("aria-hidden", "true");
      host.appendChild(brand);
    }

    for (const child of Array.from(host.children)) {
      if (child !== brand) {
        child.classList.add("friday-original-google-brand");
      }
    }
    host.classList.add("friday-google-brand-host");
    host.setAttribute("aria-label", "FRIDAY Search home");
    host.setAttribute("title", "FRIDAY Search - results powered by Google");
  }

  function scheduleBrandUpdate() {
    if (updateScheduled) {
      return;
    }
    updateScheduled = true;
    window.requestAnimationFrame(() => {
      updateScheduled = false;
      applyFridayBrand();
    });
  }

  applyFridayBrand();
  new MutationObserver(scheduleBrandUpdate).observe(document.documentElement, {
    childList: true,
    subtree: true,
  });
})();
