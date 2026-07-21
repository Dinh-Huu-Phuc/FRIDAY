const API_ORIGINS = ["http://127.0.0.1:8001", "http://localhost:8001"]

async function bridgeRequest(path, options = {}) {
  let lastError = null
  for (const origin of API_ORIGINS) {
    try {
      const response = await fetch(`${origin}${path}`, {
        method: options.method || "GET",
        headers: options.body ? { "Content-Type": "application/json" } : undefined,
        body: options.body ? JSON.stringify(options.body) : undefined,
        cache: "no-store",
      })
      const payload = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`)
      return payload
    } catch (error) {
      lastError = error
    }
  }
  throw lastError || new Error("FRIDAY Local Core is unavailable")
}

async function openMessenger() {
  const tabs = await chrome.tabs.query({ url: "https://www.messenger.com/*" })
  const messagesTab = tabs[0]
  if (messagesTab?.id) {
    await chrome.tabs.update(messagesTab.id, { active: true })
    if (messagesTab.windowId) await chrome.windows.update(messagesTab.windowId, { focused: true })
    return messagesTab.id
  }
  const tab = await chrome.tabs.create({ url: "https://www.messenger.com/", active: true })
  return tab.id
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type === "BRIDGE_REQUEST") {
    bridgeRequest(message.path, { method: message.method, body: message.body })
      .then((payload) => sendResponse({ ok: true, payload }))
      .catch((error) => sendResponse({ ok: false, error: error?.message || String(error) }))
    return true
  }

  if (message?.type === "OPEN_MESSENGER") {
    openMessenger()
      .then((tabId) => sendResponse({ ok: true, tabId }))
      .catch((error) => sendResponse({ ok: false, error: error?.message || String(error) }))
    return true
  }

  if (message?.type === "BRIDGE_STATUS") {
    chrome.storage.local.set({
      bridgeStatus: {
        connected: Boolean(message.connected),
        detail: String(message.detail || ""),
        updatedAt: Date.now(),
        pageUrl: String(sender.tab?.url || ""),
      },
    })
  }
  return false
})

chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.local.set({
    bridgeStatus: {
      connected: false,
      detail: "Open Messenger and start FRIDAY Local Core.",
      updatedAt: Date.now(),
      pageUrl: "",
    },
  })
})
