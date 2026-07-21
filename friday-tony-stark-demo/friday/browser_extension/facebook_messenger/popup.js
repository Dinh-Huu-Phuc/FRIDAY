const statusDot = document.querySelector("#status-dot")
const statusText = document.querySelector("#status-text")
const openMessagesButton = document.querySelector("#open-messages")

chrome.storage.local.get("bridgeStatus").then(({ bridgeStatus }) => {
  const status = bridgeStatus || {}
  const fresh = Date.now() - Number(status.updatedAt || 0) < 10000
  const connected = Boolean(status.connected && fresh)
  statusDot.classList.add(connected ? "connected" : "disconnected")
  statusText.textContent = connected
    ? status.detail || "Connected to FRIDAY Local Core"
    : "Open Messenger and start FRIDAY Local Core"
})

openMessagesButton.addEventListener("click", async () => {
  await chrome.runtime.sendMessage({ type: "OPEN_MESSENGER" })
  window.close()
})
