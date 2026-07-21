const panel = document.querySelector(".access-panel")
const form = document.querySelector("#access-form")
const title = document.querySelector("#access-title")
const subtitle = document.querySelector("#access-subtitle")
const modeLabel = document.querySelector("#mode-label")
const passwordLabel = document.querySelector("#password-label")
const passwordInput = document.querySelector("#password")
const confirmationField = document.querySelector("#confirmation-field")
const confirmationInput = document.querySelector("#confirmation")
const errorLabel = document.querySelector("#access-error")
const submitButton = document.querySelector("#submit-button")
const submitLabel = document.querySelector("#submit-label")
const recoveryNote = document.querySelector("#recovery-note")

let mode = "unlock"

function setBusy(busy) {
  submitButton.disabled = busy
  passwordInput.disabled = busy
  confirmationInput.disabled = busy
  if (busy) submitLabel.textContent = mode === "setup" ? "Securing core" : "Authenticating"
  else submitLabel.textContent = mode === "setup" ? "Create passcode" : "Unlock core"
}

function showError(message) {
  panel.dataset.state = "error"
  errorLabel.textContent = message || "Unable to authenticate."
}

function configureMode(configured) {
  mode = configured ? "unlock" : "setup"
  panel.dataset.state = mode
  form.hidden = false
  confirmationField.hidden = configured
  confirmationInput.required = !configured
  recoveryNote.hidden = configured
  passwordInput.autocomplete = configured ? "current-password" : "new-password"
  passwordLabel.textContent = configured ? "Passcode" : "New passcode"
  modeLabel.textContent = configured ? "Core locked" : "First-time initialization"
  title.textContent = configured ? "Welcome back" : "Create core passcode"
  subtitle.textContent = configured
    ? "Authenticate to enter FRIDAY Local Core."
    : "This passcode is permanent. Store it somewhere private."
  setBusy(false)
  passwordInput.focus()
}

async function readJson(response) {
  try {
    return await response.json()
  } catch {
    return {}
  }
}

async function loadStatus() {
  try {
    const response = await fetch("/ui/access/status", {
      credentials: "same-origin",
      cache: "no-store",
    })
    if (!response.ok) throw new Error("Secure storage is unavailable.")
    const status = await response.json()
    if (status.unlocked) {
      window.location.replace("/ui")
      return
    }
    configureMode(Boolean(status.configured))
  } catch (error) {
    modeLabel.textContent = "Connection error"
    title.textContent = "Core unavailable"
    subtitle.textContent = "Check the database connection and restart friday-api."
    showError(error instanceof Error ? error.message : "Secure storage is unavailable.")
  }
}

form.addEventListener("submit", async (event) => {
  event.preventDefault()
  errorLabel.textContent = ""
  panel.dataset.state = mode
  setBusy(true)

  const payload = { password: passwordInput.value }
  if (mode === "setup") payload.confirmation = confirmationInput.value

  try {
    const response = await fetch(`/ui/access/${mode}`, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    const result = await readJson(response)
    if (!response.ok) throw new Error(result.detail || "Unable to authenticate.")
    window.location.replace(result.next || "/ui")
  } catch (error) {
    showError(error instanceof Error ? error.message : "Unable to authenticate.")
    passwordInput.value = ""
    confirmationInput.value = ""
    passwordInput.focus()
    setBusy(false)
  }
})

void loadStatus()
