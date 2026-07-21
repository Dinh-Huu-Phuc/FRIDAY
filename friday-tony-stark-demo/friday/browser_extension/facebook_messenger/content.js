const COMMAND_PATH = "/api/v1/browser-bridge/messenger/command"
const SNAPSHOT_PATH = "/api/v1/browser-bridge/messenger/snapshot"
const POLL_INTERVAL_MS = 1500

let pollInFlight = false
let lastCompletedRequestId = ""

function normalizeText(value) {
  return String(value || "")
    .replace(/Đ/g, "D")
    .replace(/đ/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim()
}

function compactLines(value) {
  const ignored = new Set([
    "active now", "dang hoat dong", "more", "xem them", "open chat",
    "mo doan chat", "profile picture", "anh dai dien", "react",
  ])
  const output = []
  for (const rawLine of String(value || "").split("\n")) {
    const line = rawLine.replace(/\s+/g, " ").trim()
    if (!line || ignored.has(normalizeText(line)) || output.includes(line)) continue
    output.push(line)
  }
  return output
}

function isTimestamp(value) {
  return /^(?:\d{1,2}:\d{2}(?:\s*[ap]m)?|\d+\s*(?:m|h|d|min|hr|day)s?|\d+\s*(?:phut|gio|ngay|tuan)|hom qua|hom nay|t[2-7]|cn|yesterday|today|mon|tue|wed|thu|fri|sat|sun)$/i.test(normalizeText(value))
}

function isVisible(element) {
  const rect = element.getBoundingClientRect()
  const style = getComputedStyle(element)
  return rect.width > 1 && rect.height > 1 && style.visibility !== "hidden" && style.display !== "none"
}

function hasUnreadMarker(element) {
  const labels = [...element.querySelectorAll("[aria-label]")]
    .map((item) => item.getAttribute("aria-label") || "")
  const combined = normalizeText(`${element.getAttribute("aria-label") || ""} ${labels.join(" ")}`)
  return ["unread", "new message", "mark as read", "chua doc", "tin nhan moi", "danh dau la da doc"]
    .some((token) => combined.includes(token))
}

function rowCandidates() {
  const selectors = [
    'a[href*="/messages/t/"]',
    'a[href*="/messages/e2ee/t/"]',
    '[role="dialog"] a[href*="/t/"]',
    '[role="main"] a[href*="/t/"]',
  ]
  const candidates = selectors.flatMap((selector) => [...document.querySelectorAll(selector)])
  const seen = new Set()
  return candidates.filter((element) => {
    const url = element.href || element.getAttribute("href") || ""
    if (!url || seen.has(url) || !isVisible(element)) return false
    seen.add(url)
    return true
  })
}

function extractConversations() {
  const conversations = []
  for (const row of rowCandidates().slice(0, 30)) {
    const lines = compactLines(row.innerText)
    if (lines.length < 2) continue
    const sender = lines[0]
    const timestamp = lines.slice(1).find(isTimestamp) || ""
    const preview = lines.slice(1).filter((line) => line !== timestamp).join(" ").trim()
    if (!sender || !preview) continue
    conversations.push({
      sender,
      preview,
      timestamp,
      unread: hasUnreadMarker(row),
      url: String(row.href || row.getAttribute("href") || ""),
    })
  }
  return conversations
}

function wait(milliseconds) {
  return new Promise((resolve) => setTimeout(resolve, milliseconds))
}

function bridgeRequest(path, options = {}) {
  return chrome.runtime.sendMessage({
    type: "BRIDGE_REQUEST",
    path,
    method: options.method || "GET",
    body: options.body,
  }).then((response) => {
    if (!response?.ok) throw new Error(response?.error || "FRIDAY bridge request failed")
    return response.payload
  })
}

async function scanCurrentMessengerPage() {
  let conversations = extractConversations()
  if (conversations.length) return conversations
  await wait(1800)
  return extractConversations()
}

async function pollBridge() {
  if (pollInFlight) return
  pollInFlight = true
  try {
    const payload = await bridgeRequest(COMMAND_PATH)
    chrome.runtime.sendMessage({ type: "BRIDGE_STATUS", connected: true, detail: "Connected to FRIDAY Local Core" })
    const command = payload?.command
    if (!command?.request_id || command.request_id === lastCompletedRequestId) return

    const conversations = await scanCurrentMessengerPage()
    if (!conversations.length) return
    await bridgeRequest(SNAPSHOT_PATH, {
      method: "POST",
      body: {
        request_id: command.request_id,
        page_url: location.href,
        conversations,
      },
    })
    lastCompletedRequestId = command.request_id
    chrome.runtime.sendMessage({ type: "BRIDGE_STATUS", connected: true, detail: "Latest Messenger preview synchronized" })
  } catch (error) {
    chrome.runtime.sendMessage({
      type: "BRIDGE_STATUS",
      connected: false,
      detail: error?.message || String(error),
    })
  } finally {
    pollInFlight = false
  }
}

pollBridge()
setInterval(pollBridge, POLL_INTERVAL_MS)
