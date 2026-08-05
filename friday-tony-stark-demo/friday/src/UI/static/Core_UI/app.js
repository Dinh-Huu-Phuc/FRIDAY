const STORAGE_KEY = "friday.localCore.appearance"

const defaults = {
  primaryColor: "#5bdcff",
  secondaryColor: "#ffc768",
  glowIntensity: 1,
  pulseSpeed: 1,
  orbSize: 260,
  coreVisual: "orb",
  voiceReactive: true,
  reduceMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  voiceEnabled: true,
  historyVisible: true,
}

const state = {
  socket: null,
  calendarEvents: null,
  coreState: "disconnected",
  powerState: "active",
  voiceUnlocked: false,
  voiceUnlockedAt: 0,
  pendingSpeech: "",
  speechActive: false,
  speechQueue: [],
  lastAssistantId: "",
  messages: [],
  expandedCards: new Set(),
  recognition: null,
  recognitionWanted: true,
  recognitionBlocked: false,
  recognitionPausedForSpeech: false,
  recognitionRestartTimer: 0,
  microphoneStream: null,
  microphoneContext: null,
  microphoneAnalyser: null,
  microphoneWorklet: null,
  microphoneWorkletGain: null,
  microphoneRecorder: null,
  microphoneHeader: null,
  microphoneFrame: 0,
  microphonePaused: false,
  microphoneTranscribing: false,
  microphoneCapturing: false,
  microphoneSilenceAt: 0,
  microphoneNoiseFloor: 0.003,
  microphoneVoiceFrames: 0,
  microphoneCaptureStartedAt: 0,
  microphoneCapturePeak: 0,
  microphoneChunks: [],
  microphonePreRoll: [],
  microphoneLevels: Array(30).fill(0),
  pendingWindowAction: "",
  windowActionTimer: 0,
  settings: loadSettings(),
}

const root = document.querySelector(".app-shell")
const messagesEl = document.querySelector("#messages")
const historyDock = document.querySelector("#history-dock")
const form = document.querySelector("#chat-form")
const input = document.querySelector("#message-input")
const statusLabel = document.querySelector("#status")
const transport = document.querySelector("#transport")
const clearChat = document.querySelector("#clear-chat")
const toggleHistory = document.querySelector("#toggle-history")
const micButton = document.querySelector("#mic-button")
const micWaveform = document.querySelector("#mic-waveform")
const connectionIndicator = document.querySelector("#connection-indicator")
const connectionPopover = document.querySelector("#connection-popover")
const coreServiceStatus = document.querySelector("#core-service-status")
const websocketStatus = document.querySelector("#websocket-status")
const voiceStatus = document.querySelector("#voice-status")
const settingsToggle = document.querySelector("#settings-toggle")
const settingsPanel = document.querySelector("#settings-panel")
const settingsClose = document.querySelector("#settings-close")
const sleepTime = document.querySelector("#sleep-time")
const sleepDate = document.querySelector("#sleep-date")
const coreVideoLayer = document.querySelector("#core-video-layer")
const coreVideo = document.querySelector("#core-video")
const coreVideoMessage = document.querySelector("#core-video-message")
const visualControls = [...document.querySelectorAll('input[name="core-visual"]')]
const autoSleepMinutes = document.querySelector("#auto-sleep-minutes")
const autoSleepStatus = document.querySelector("#auto-sleep-status")
const autoSleepFeedback = document.querySelector("#auto-sleep-feedback")
const applyAutoSleep = document.querySelector("#apply-auto-sleep")

const controls = {
  primaryColor: document.querySelector("#primary-color"),
  secondaryColor: document.querySelector("#secondary-color"),
  glowIntensity: document.querySelector("#glow-intensity"),
  pulseSpeed: document.querySelector("#pulse-speed"),
  orbSize: document.querySelector("#orb-size"),
  voiceReactive: document.querySelector("#voice-reactive"),
  reduceMotion: document.querySelector("#reduce-motion"),
  voiceEnabled: document.querySelector("#voice-enabled"),
}

function loadSettings() {
  try {
    return { ...defaults, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}") }
  } catch {
    return { ...defaults }
  }
}

function saveSettings() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state.settings))
}

function hexToRgb(hex) {
  const normalized = String(hex || "").replace("#", "")
  if (!/^[0-9a-fA-F]{6}$/.test(normalized)) return "91, 220, 255"
  return [
    parseInt(normalized.slice(0, 2), 16),
    parseInt(normalized.slice(2, 4), 16),
    parseInt(normalized.slice(4, 6), 16),
  ].join(", ")
}

function setCoreState(nextState, label) {
  state.coreState = nextState
  root.dataset.coreState = nextState
  statusLabel.textContent = label
  transport.textContent = nextState === "disconnected" ? "offline" : nextState === "error" ? "error" : "online"
  websocketStatus.textContent = nextState === "disconnected" ? "disconnected" : nextState
  connectionIndicator.dataset.status =
    nextState === "disconnected" || nextState === "error" ? nextState : nextState === "reconnecting" ? "reconnecting" : "connected"
}

function setPowerState(payload) {
  const previousPowerState = state.powerState
  state.powerState = payload?.state === "sleeping" ? "sleeping" : "active"
  root.dataset.powerState = state.powerState
  if (state.powerState === "sleeping") {
    if (previousPowerState !== "sleeping") queueWindowAction("minimize")
    setCoreState("sleeping", "Sleeping. Say FRIDAY wake up")
    return
  }
  if (previousPowerState === "sleeping") {
    state.pendingWindowAction = ""
    window.clearTimeout(state.windowActionTimer)
  }
  if (state.coreState === "sleeping") setCoreState("idle", "Awake and ready")
}

function updateSleepClock() {
  const now = new Date()
  sleepTime.textContent = new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(now)
  sleepDate.textContent = new Intl.DateTimeFormat("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  }).format(now)
}

async function performWindowAction(action) {
  const endpoint = action === "restore" ? "restore" : "minimize"
  try {
    await fetch(`/api/v1/runtime/windows/${endpoint}`, { method: "POST" })
  } catch {
    if (action === "restore") setCoreState("error", "Could not restore application windows")
  }
}

function queueWindowAction(action) {
  state.pendingWindowAction = action
  window.clearTimeout(state.windowActionTimer)
  const delay = state.settings.voiceEnabled ? 8000 : 600
  state.windowActionTimer = window.setTimeout(() => runPendingWindowAction(), delay)
}

function runPendingWindowAction() {
  const action = state.pendingWindowAction
  state.pendingWindowAction = ""
  window.clearTimeout(state.windowActionTimer)
  if (action) void performWindowAction(action)
}

function applyAppearance() {
  const settings = state.settings
  const coreVisual = settings.coreVisual === "video" ? "video" : "orb"
  settings.coreVisual = coreVisual
  root.style.setProperty("--primary", settings.primaryColor)
  root.style.setProperty("--secondary", settings.secondaryColor)
  root.style.setProperty("--primary-rgb", hexToRgb(settings.primaryColor))
  root.style.setProperty("--secondary-rgb", hexToRgb(settings.secondaryColor))
  root.style.setProperty("--glow-intensity", settings.glowIntensity)
  root.style.setProperty("--pulse-speed", `${settings.pulseSpeed}s`)
  root.style.setProperty("--orb-size", `${settings.orbSize}px`)
  root.dataset.reduceMotion = settings.reduceMotion ? "true" : "false"
  root.dataset.voiceReactive = settings.voiceReactive ? "true" : "false"
  root.dataset.coreVisual = coreVisual
  historyDock.dataset.collapsed = settings.historyVisible ? "false" : "true"
  toggleHistory.textContent = settings.historyVisible ? "Hide" : "Show"
  visualControls.forEach((control) => { control.checked = control.value === coreVisual })

  for (const [key, control] of Object.entries(controls)) {
    if (!control) continue
    if (control.type === "checkbox") control.checked = Boolean(settings[key])
    else control.value = settings[key]
  }
  applyCoreVisual()
  voiceStatus.textContent = settings.voiceEnabled ? (state.voiceUnlocked ? "enabled" : "waiting for gesture") : "disabled"
}

function applyCoreVisual() {
  const useVideo = state.settings.coreVisual === "video"
  coreVideoLayer.dataset.active = useVideo ? "true" : "false"
  if (!useVideo) {
    coreVideo.pause()
    coreVideoLayer.dataset.playback = "paused"
    return
  }
  if (!coreVideo.src) {
    coreVideoLayer.dataset.playback = "loading"
    coreVideo.src = coreVideo.dataset.src
    coreVideo.load()
  }
  if (state.settings.reduceMotion) {
    showCoreVideoFrame()
    return
  }
  playCoreVideo()
}

function showCoreVideoFrame() {
  const pauseOnFrame = () => {
    coreVideo.pause()
    coreVideoLayer.dataset.playback = "ready"
  }
  if (coreVideo.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) pauseOnFrame()
  else coreVideo.addEventListener("loadeddata", pauseOnFrame, { once: true })
}

function playCoreVideo() {
  coreVideo.muted = true
  const playback = coreVideo.play()
  if (!playback?.then) return
  void playback.then(() => {
    coreVideoLayer.dataset.playback = "playing"
  }).catch(() => {
    coreVideoLayer.dataset.playback = "blocked"
    coreVideo.addEventListener("canplay", () => {
      if (state.settings.coreVisual === "video" && !state.settings.reduceMotion) {
        void coreVideo.play().catch(() => null)
      }
    }, { once: true })
  })
}

function updateSetting(key, value) {
  state.settings[key] = value
  saveSettings()
  applyAppearance()
}

function bindAudioReactive(audio) {
  if (!state.settings.voiceReactive || !window.AudioContext) return () => {}
  const audioContext = new AudioContext()
  const source = audioContext.createMediaElementSource(audio)
  const analyser = audioContext.createAnalyser()
  analyser.fftSize = 128
  source.connect(analyser)
  analyser.connect(audioContext.destination)

  const samples = new Uint8Array(analyser.frequencyBinCount)
  let frame = 0
  const tick = () => {
    analyser.getByteFrequencyData(samples)
    const sum = samples.reduce((total, value) => total + value, 0)
    const level = Math.min(1, sum / samples.length / 140)
    root.style.setProperty("--voice-level", level.toFixed(3))
    frame = window.requestAnimationFrame(tick)
  }
  frame = window.requestAnimationFrame(tick)

  return () => {
    window.cancelAnimationFrame(frame)
    root.style.setProperty("--voice-level", "0")
    void audioContext.close().catch(() => null)
  }
}

function ConversationCard(message, index, total) {
  const node = document.createElement("article")
  const role = message.role === "user" ? "user" : message.role === "system" ? "system" : "assistant"
  const age = total - index - 1
  const expanded = state.expandedCards.has(message.id)
  node.className = `conversation-card ${role}${expanded ? " expanded" : ""}`
  node.style.setProperty("--age", Math.min(age, 6))
  node.dataset.id = message.id

  const meta = document.createElement("span")
  meta.className = "card-meta"
  meta.textContent = `${role === "assistant" ? "FRIDAY" : role.toUpperCase()} / ${new Date(message.timestamp).toLocaleTimeString()}`

  const content = document.createElement("p")
  content.className = "conversation-content"
  content.textContent = message.content
  renderConversationMath(content)

  const copyButton = document.createElement("button")
  copyButton.className = "conversation-copy"
  copyButton.type = "button"
  copyButton.title = "Copy message"
  copyButton.setAttribute("aria-label", "Copy message")

  const copyIcon = document.createElement("img")
  copyIcon.src = "/ui/assets/icons/clone.svg"
  copyIcon.alt = ""
  copyIcon.setAttribute("aria-hidden", "true")
  copyButton.append(copyIcon)
  copyButton.addEventListener("click", async (event) => {
    event.stopPropagation()
    const copied = await copyText(message.content)
    copyButton.dataset.state = copied ? "copied" : "failed"
    copyButton.title = copied ? "Copied" : "Copy failed"
    copyButton.setAttribute("aria-label", copyButton.title)
    window.setTimeout(() => {
      delete copyButton.dataset.state
      copyButton.title = "Copy message"
      copyButton.setAttribute("aria-label", "Copy message")
    }, 1400)
  })

  node.append(meta, copyButton, content)
  node.addEventListener("click", () => {
    if (state.expandedCards.has(message.id)) state.expandedCards.delete(message.id)
    else state.expandedCards.add(message.id)
    ConversationStack(state.messages)
  })
  return node
}

function renderConversationMath(element) {
  if (typeof window.renderMathInElement !== "function") return
  window.renderMathInElement(element, {
    delimiters: [
      { left: "$$", right: "$$", display: true },
      { left: "\\[", right: "\\]", display: true },
      { left: "\\(", right: "\\)", display: false },
      { left: "$", right: "$", display: false },
    ],
    throwOnError: false,
    strict: "ignore",
    trust: false,
  })
}

async function copyText(text) {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // Fall through for browsers where clipboard access is unavailable.
  }

  const textarea = document.createElement("textarea")
  textarea.value = text
  textarea.setAttribute("readonly", "")
  textarea.className = "clipboard-fallback"
  document.body.append(textarea)
  textarea.select()
  const copied = document.execCommand("copy")
  textarea.remove()
  return copied
}

function ConversationStack(items) {
  const visible = (items || []).filter((item) => item.id !== "console-bootstrap")
  messagesEl.replaceChildren()
  visible.forEach((item, index) => messagesEl.append(ConversationCard(item, index, visible.length)))
  messagesEl.scrollTop = messagesEl.scrollHeight

  const latestAssistant = [...visible].reverse().find((item) => item.role === "assistant")
  if (latestAssistant && latestAssistant.id !== state.lastAssistantId) {
    state.lastAssistantId = latestAssistant.id
    void VoiceController.speak(latestAssistant.content)
  }
}

const VoiceController = {
  async speak(text) {
    if (!state.settings.voiceEnabled || !text) return
    if (!state.voiceUnlocked) {
      state.pendingSpeech = text
      setCoreState("idle", "Voice will start after your first click")
      voiceStatus.textContent = "waiting for gesture"
      return
    }
    if (state.speechActive) {
      state.speechQueue.push(text)
      return
    }

    state.speechActive = true
    SpeechInputController.pauseForSpeech()
    setCoreState("speaking", "Speaking")
    try {
      const response = await fetch("/api/v1/agent/tts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text.slice(0, 1800), provider: "auto" }),
      })
      if (!response.ok) throw new Error("Backend TTS unavailable")
      const blob = await response.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      const stopReactive = bindAudioReactive(audio)
      audio.onended = () => {
        stopReactive()
        URL.revokeObjectURL(url)
        this.finishSpeech()
      }
      audio.onerror = () => {
        stopReactive()
        URL.revokeObjectURL(url)
        this.finishSpeech("Voice playback failed")
      }
      await audio.play()
    } catch {
      if (!window.speechSynthesis) {
        this.finishSpeech("Voice unavailable")
        return
      }
      const utterance = new SpeechSynthesisUtterance(text.slice(0, 1800))
      utterance.lang = "en-US"
      utterance.onend = () => {
        this.finishSpeech()
      }
      utterance.onerror = () => {
        this.finishSpeech("Voice synthesis failed")
      }
      window.speechSynthesis.cancel()
      window.speechSynthesis.speak(utterance)
    }
  },
  finishSpeech(errorMessage = "") {
    state.speechActive = false
    const next = state.speechQueue.shift()
    if (next) {
      void this.speak(next)
      return
    }
    SpeechInputController.resumeAfterSpeech()
    runPendingWindowAction()
    if (errorMessage) setCoreState("error", errorMessage)
    else if (state.powerState === "sleeping") setCoreState("sleeping", "Sleeping. Say FRIDAY wake up")
    else setCoreState("idle", "Local connected")
  },
  unlock() {
    if (state.voiceUnlocked) return
    state.voiceUnlocked = true
    state.voiceUnlockedAt = Date.now()
    voiceStatus.textContent = state.settings.voiceEnabled ? "enabled" : "disabled"
    if (window.speechSynthesis) window.speechSynthesis.cancel()
    const pending = state.pendingSpeech
    state.pendingSpeech = ""
    if (pending) void this.speak(pending)
  },
}

function sendMessage(message, channel = "text") {
  const normalized = message.trim()
  if (!normalized || state.socket?.readyState !== WebSocket.OPEN) return
  state.socket.send(JSON.stringify({ message: normalized, channel }))
  input.value = ""
  input.style.height = "auto"
  if (state.powerState !== "sleeping") setCoreState("thinking", "Thinking")
}

const SpeechInputController = {
  supported() {
    return Boolean(navigator.mediaDevices?.getUserMedia && window.MediaRecorder && window.AudioContext)
  },
  async start({ userInitiated = false } = {}) {
    if (!this.supported()) {
      voiceStatus.textContent = "unsupported"
      return
    }
    if (userInitiated) {
      state.recognitionBlocked = false
      state.recognitionWanted = true
    }
    if (state.microphoneStream) {
      state.microphonePaused = false
      await this.resumeAudioContext()
      voiceStatus.textContent = "always listening"
      return
    }
    if (state.recognitionBlocked || !state.recognitionWanted) {
      state.microphonePaused = false
      return
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      const context = new AudioContext()
      await context.resume().catch(() => null)
      const source = context.createMediaStreamSource(stream)
      const analyser = context.createAnalyser()
      analyser.fftSize = 512
      analyser.smoothingTimeConstant = 0.24
      source.connect(analyser)

      let worklet = null
      let workletGain = null
      if (context.audioWorklet && window.AudioWorkletNode) {
        try {
          await context.audioWorklet.addModule(
            "/ui/static/Core_UI/mic-level-processor.js?v=20260721-wake",
          )
          worklet = new AudioWorkletNode(context, "friday-mic-level")
          worklet.port.addEventListener("message", (event) => {
            this.onAudioLevel(Number(event.data?.rms || 0))
          })
          worklet.port.start()
          workletGain = context.createGain()
          workletGain.gain.value = 0
          source.connect(worklet)
          worklet.connect(workletGain)
          workletGain.connect(context.destination)
        } catch {
          worklet?.disconnect()
          workletGain?.disconnect()
          worklet = null
          workletGain = null
        }
      }

      const preferredType = "audio/webm;codecs=opus"
      const options = MediaRecorder.isTypeSupported(preferredType)
        ? { mimeType: preferredType }
        : undefined
      const recorder = new MediaRecorder(stream, options)
      recorder.addEventListener("dataavailable", (event) => this.onAudioChunk(event.data))
      recorder.start(200)

      state.microphoneStream = stream
      state.microphoneContext = context
      state.microphoneAnalyser = analyser
      state.microphoneWorklet = worklet
      state.microphoneWorkletGain = workletGain
      state.microphoneRecorder = recorder
      state.microphonePaused = false
      state.recognitionBlocked = false
      voiceStatus.textContent = "always listening"
      micButton.dataset.active = "true"
      this.monitorLevel()
    } catch (error) {
      state.recognitionBlocked = true
      voiceStatus.textContent = "permission required"
      micButton.dataset.active = "false"
      setCoreState("error", `Microphone unavailable: ${error?.message || "permission denied"}`)
    }
  },
  async resumeAudioContext() {
    const context = state.microphoneContext
    if (context?.state === "suspended") {
      await context.resume().catch(() => null)
    }
  },
  onAudioChunk(chunk) {
    if (!chunk?.size) return
    if (!state.microphoneHeader) state.microphoneHeader = chunk
    if (state.microphoneCapturing) {
      state.microphoneChunks.push(chunk)
      return
    }
    state.microphonePreRoll.push(chunk)
    state.microphonePreRoll = state.microphonePreRoll.slice(-2)
  },
  monitorLevel() {
    window.cancelAnimationFrame(state.microphoneFrame)
    if (state.microphoneWorklet) return
    const analyser = state.microphoneAnalyser
    if (!analyser) return
    const samples = new Float32Array(analyser.fftSize)
    const tick = () => {
      if (!state.microphoneAnalyser) return
      analyser.getFloatTimeDomainData(samples)
      let energy = 0
      for (const sample of samples) energy += sample * sample
      this.onAudioLevel(Math.sqrt(energy / samples.length))
      state.microphoneFrame = window.requestAnimationFrame(tick)
    }
    tick()
  },
  onAudioLevel(rms) {
    if (!Number.isFinite(rms)) return
    drawMicrophoneWaveform(Math.min(1, rms / 0.08))

    if (state.microphonePaused || state.microphoneTranscribing) {
      state.microphoneCapturing = false
      state.microphoneChunks = []
      state.microphoneSilenceAt = 0
      state.microphoneVoiceFrames = 0
      state.microphoneCaptureStartedAt = 0
      state.microphoneCapturePeak = 0
      return
    }

    const sleeping = state.powerState === "sleeping"
    const threshold = sleeping
      ? Math.max(0.014, state.microphoneNoiseFloor * 5)
      : Math.max(0.006, state.microphoneNoiseFloor * 3.2)
    const requiredVoiceFrames = sleeping ? 6 : 3
    if (rms >= threshold) {
      state.microphoneVoiceFrames += 1
      if (!state.microphoneCapturing && state.microphoneVoiceFrames >= requiredVoiceFrames) {
        state.microphoneCapturing = true
        state.microphoneCaptureStartedAt = performance.now()
        state.microphoneCapturePeak = rms
        state.microphoneChunks = [...state.microphonePreRoll]
        state.microphonePreRoll = []
        voiceStatus.textContent = "hearing speech"
        if (state.powerState !== "sleeping") setCoreState("listening", "FRIDAY is listening")
      }
      if (state.microphoneCapturing) {
        state.microphoneCapturePeak = Math.max(state.microphoneCapturePeak, rms)
        state.microphoneSilenceAt = 0
      }
      return
    }

    state.microphoneVoiceFrames = 0
    if (!state.microphoneCapturing) {
      if (rms < Math.max(0.012, state.microphoneNoiseFloor * 2)) {
        state.microphoneNoiseFloor = Math.max(
          0.0015,
          Math.min(0.008, state.microphoneNoiseFloor * 0.95 + rms * 0.05),
        )
      }
      return
    }
    if (!state.microphoneSilenceAt) state.microphoneSilenceAt = performance.now()
    if (performance.now() - state.microphoneSilenceAt >= 700) void this.finishUtterance()
  },
  async finishUtterance() {
    if (!state.microphoneCapturing || state.microphoneTranscribing) return
    state.microphoneCapturing = false
    state.microphoneSilenceAt = 0
    state.microphoneVoiceFrames = 0
    const captureDuration = state.microphoneCaptureStartedAt
      ? performance.now() - state.microphoneCaptureStartedAt
      : 0
    const capturePeak = state.microphoneCapturePeak
    state.microphoneCaptureStartedAt = 0
    state.microphoneCapturePeak = 0
    const chunks = state.microphoneChunks
    state.microphoneChunks = []
    state.microphonePreRoll = []
    if (!chunks.length) return

    const contentType = state.microphoneRecorder?.mimeType || chunks[0].type || "audio/webm"
    const completeChunks = state.microphoneHeader && chunks[0] !== state.microphoneHeader
      ? [state.microphoneHeader, ...chunks]
      : chunks
    const audio = new Blob(completeChunks, { type: contentType })
    if (audio.size < 2_000) return
    if (state.powerState === "sleeping" && (captureDuration < 500 || capturePeak < 0.014)) {
      voiceStatus.textContent = "always listening"
      return
    }
    state.microphoneTranscribing = true
    voiceStatus.textContent = "transcribing"
    micButton.dataset.active = "processing"
    try {
      const response = await fetch("/api/v1/agent/stt", {
        method: "POST",
        headers: {
          "Content-Type": contentType,
          "X-STT-Language": "en",
        },
        body: audio,
      })
      const payload = await response.json()
      if (!response.ok || !payload.ok) throw new Error(payload.message || `HTTP ${response.status}`)
      const transcript = String(payload.refined_text || payload.raw_text || "").trim()
      if (transcript) {
        voiceStatus.textContent = `heard: ${transcript.slice(0, 80)}`
        sendMessage(transcript, "voice")
      }
    } catch (error) {
      setCoreState("error", `Voice input failed: ${error?.message || "STT unavailable"}`)
    } finally {
      state.microphoneTranscribing = false
      voiceStatus.textContent = "always listening"
      micButton.dataset.active = "true"
    }
  },
  pauseForSpeech() {
    state.recognitionPausedForSpeech = true
    state.microphonePaused = true
    state.microphoneCapturing = false
    state.microphoneChunks = []
    state.microphoneVoiceFrames = 0
    state.microphoneCaptureStartedAt = 0
    state.microphoneCapturePeak = 0
  },
  resumeAfterSpeech() {
    state.recognitionPausedForSpeech = false
    state.microphonePaused = false
    voiceStatus.textContent = state.microphoneStream ? "always listening" : "waiting for permission"
  },
  stop() {
    window.cancelAnimationFrame(state.microphoneFrame)
    if (state.microphoneRecorder?.state !== "inactive") state.microphoneRecorder.stop()
    state.microphoneStream?.getTracks().forEach((track) => track.stop())
    state.microphoneWorklet?.disconnect()
    state.microphoneWorkletGain?.disconnect()
    void state.microphoneContext?.close().catch(() => null)
    state.microphoneStream = null
    state.microphoneContext = null
    state.microphoneAnalyser = null
    state.microphoneWorklet = null
    state.microphoneWorkletGain = null
    state.microphoneRecorder = null
    state.microphoneHeader = null
    drawMicrophoneWaveform(0)
  },
}

function drawMicrophoneWaveform(level) {
  const context = micWaveform?.getContext("2d")
  if (!context) return
  state.microphoneLevels.push(Math.max(0, Math.min(1, Number(level) || 0)))
  state.microphoneLevels = state.microphoneLevels.slice(-30)
  const width = micWaveform.width
  const height = micWaveform.height
  context.clearRect(0, 0, width, height)
  context.strokeStyle = "rgba(91, 220, 255, 0.18)"
  context.beginPath()
  context.moveTo(0, height / 2)
  context.lineTo(width, height / 2)
  context.stroke()
  const spacing = width / state.microphoneLevels.length
  state.microphoneLevels.forEach((sample, index) => {
    const barHeight = Math.max(2, sample * (height - 4))
    context.strokeStyle = sample > 0.72 ? "#ffc768" : `rgba(91, 220, 255, ${0.38 + sample * 0.62})`
    context.lineWidth = 2
    context.lineCap = "round"
    context.beginPath()
    context.moveTo((index + 0.5) * spacing, (height - barHeight) / 2)
    context.lineTo((index + 0.5) * spacing, (height + barHeight) / 2)
    context.stroke()
  })
}

function PromptInput() {

  form.addEventListener("submit", (event) => {
    event.preventDefault()
    sendMessage(input.value)
  })

  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault()
      sendMessage(input.value)
    }
  })

  input.addEventListener("input", () => {
    input.style.height = "auto"
    input.style.height = `${Math.min(input.scrollHeight, 150)}px`
  })

  micButton.addEventListener("click", () => {
    VoiceController.unlock()
    if (!SpeechInputController.supported()) {
      setCoreState("error", "Browser microphone capture unavailable")
      return
    }
    SpeechInputController.start({ userInitiated: true })
  })
}

function ConnectionIndicator() {
  connectionIndicator.addEventListener("click", () => {
    connectionPopover.hidden = !connectionPopover.hidden
  })
}

function SettingsPanel() {
  settingsToggle.addEventListener("click", () => {
    settingsPanel.hidden = false
    void loadAutoSleepSettings()
  })
  settingsClose.addEventListener("click", () => { settingsPanel.hidden = true })
  toggleHistory.addEventListener("click", () => updateSetting("historyVisible", !state.settings.historyVisible))

  controls.primaryColor.addEventListener("input", (event) => updateSetting("primaryColor", event.target.value))
  controls.secondaryColor.addEventListener("input", (event) => updateSetting("secondaryColor", event.target.value))
  controls.glowIntensity.addEventListener("input", (event) => updateSetting("glowIntensity", Number(event.target.value)))
  controls.pulseSpeed.addEventListener("input", (event) => updateSetting("pulseSpeed", Number(event.target.value)))
  controls.orbSize.addEventListener("input", (event) => updateSetting("orbSize", Number(event.target.value)))
  controls.voiceReactive.addEventListener("change", (event) => updateSetting("voiceReactive", event.target.checked))
  controls.reduceMotion.addEventListener("change", (event) => updateSetting("reduceMotion", event.target.checked))
  controls.voiceEnabled.addEventListener("change", (event) => updateSetting("voiceEnabled", event.target.checked))
  visualControls.forEach((control) => {
    control.addEventListener("change", (event) => {
      if (event.target.checked) updateSetting("coreVisual", event.target.value)
    })
  })
  applyAutoSleep.addEventListener("click", () => { void applyAutoSleepSettings() })

  coreVideo.addEventListener("loadeddata", () => {
    coreVideoLayer.dataset.playback = state.settings.reduceMotion ? "ready" : "loaded"
  })
  coreVideo.addEventListener("playing", () => { coreVideoLayer.dataset.playback = "playing" })
  coreVideo.addEventListener("waiting", () => { coreVideoLayer.dataset.playback = "loading" })
  coreVideo.addEventListener("error", () => {
    coreVideoLayer.dataset.playback = "error"
    coreVideoMessage.textContent = "FRIDAY visual could not be loaded"
  })

  clearChat.addEventListener("click", () => {
    if (state.socket?.readyState !== WebSocket.OPEN) return
    state.socket.send(JSON.stringify({ type: "clear" }))
  })
  void loadAutoSleepSettings()
}

async function loadAutoSleepSettings() {
  try {
    const response = await fetch("/api/v1/runtime/auto-sleep")
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    autoSleepMinutes.value = String(Number(payload.minutes))
    autoSleepStatus.textContent = `${Number(payload.minutes)} min`
    autoSleepFeedback.textContent = ""
    autoSleepFeedback.dataset.status = "ready"
  } catch {
    autoSleepStatus.textContent = "Unavailable"
    autoSleepFeedback.textContent = "Could not load the current timer."
    autoSleepFeedback.dataset.status = "error"
  }
}

async function applyAutoSleepSettings() {
  const minutes = Number(autoSleepMinutes.value)
  if (!Number.isFinite(minutes) || minutes < 1 || minutes > 1440) {
    autoSleepFeedback.textContent = "Enter a value from 1 to 1440 minutes."
    autoSleepFeedback.dataset.status = "error"
    autoSleepMinutes.focus()
    return
  }

  applyAutoSleep.disabled = true
  autoSleepFeedback.textContent = "Applying..."
  autoSleepFeedback.dataset.status = "pending"
  try {
    const response = await fetch("/api/v1/runtime/auto-sleep", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ minutes }),
    })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const payload = await response.json()
    autoSleepMinutes.value = String(Number(payload.minutes))
    autoSleepStatus.textContent = `${Number(payload.minutes)} min`
    autoSleepFeedback.textContent = "Applied. The idle countdown restarted."
    autoSleepFeedback.dataset.status = "success"
  } catch {
    autoSleepFeedback.textContent = "Could not apply the new timer."
    autoSleepFeedback.dataset.status = "error"
  } finally {
    applyAutoSleep.disabled = false
  }
}

function connect() {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws"
  const socket = new WebSocket(`${protocol}://${window.location.host}/ws/chat`)
  state.socket = socket
  websocketStatus.textContent = "connecting"
  setCoreState("disconnected", "Connecting to local core...")

  socket.addEventListener("open", () => {
    coreServiceStatus.textContent = "online"
    websocketStatus.textContent = "connected"
    setCoreState("idle", "Local connected")
    SpeechInputController.start()
  })
  socket.addEventListener("close", () => {
    websocketStatus.textContent = "reconnecting"
    setCoreState("reconnecting", "Reconnecting")
    window.setTimeout(connect, 1200)
  })
  socket.addEventListener("error", () => {
    setCoreState("error", "Connection error")
  })
  socket.addEventListener("message", (event) => {
    const packet = JSON.parse(event.data)
    if (packet.type === "snapshot") {
      state.messages = packet.payload.messages || []
      ConversationStack(state.messages)
      if (state.coreState !== "speaking" && state.powerState !== "sleeping") setCoreState("idle", "Local connected")
      return
    }
    if (packet.type === "power") {
      setPowerState(packet.payload)
      return
    }
    if (packet.type === "cleared") {
      state.lastAssistantId = ""
      state.expandedCards.clear()
      state.messages = packet.payload.messages || []
      ConversationStack(state.messages)
      setCoreState("idle", packet.payload.archivePath ? "Chat saved. New session ready." : "New session ready.")
      return
    }
    if (packet.type === "state") {
      if (packet.state === "thinking") setCoreState("thinking", "Thinking")
      if (packet.state === "briefing") setCoreState("thinking", "Checking weather and news")
      if (packet.state === "searching") setCoreState("thinking", "Searching")
      return
    }
    if (packet.type === "search_acknowledgement") {
      setCoreState("thinking", "Searching")
      void VoiceController.speak(packet.message)
      return
    }
    if (packet.type === "voice_ignored") {
      const heard = String(packet.message || "").slice(0, 80)
      setCoreState("sleeping", `Heard "${heard}". Say FRIDAY wake up`)
      return
    }
    if (packet.type === "error") {
      setCoreState("error", packet.message)
    }
  })
}

function connectCalendarEvents() {
  if (!window.EventSource || state.calendarEvents) return
  const events = new EventSource("/sse/agent")
  state.calendarEvents = events
  events.addEventListener("calendar_reminder", (event) => {
    let payload
    try {
      payload = JSON.parse(event.data)
    } catch {
      return
    }

    const audioTarget = String(payload.audio_target || "none")
    const browserOwnsAudio = audioTarget === "web" || audioTarget === "all"
    const message = payload.message
    if (message?.id) {
      state.messages = [
        ...state.messages.filter((item) => item.id !== message.id),
        message,
      ].slice(-80)
      if (!browserOwnsAudio) state.lastAssistantId = message.id
      ConversationStack(state.messages)
    } else if (browserOwnsAudio) {
      void VoiceController.speak(String(payload.spoken_text || ""))
    }

    if (payload.sleeping) {
      setCoreState("sleeping", "Calendar reminder delivered. FRIDAY remains asleep")
    } else if (state.coreState !== "speaking") {
      setCoreState("idle", `Reminder: ${String(payload.title || "scheduled activity")}`)
    }
  })
  events.addEventListener("error", () => {
    if (events.readyState === EventSource.CLOSED) {
      state.calendarEvents = null
    }
  })
}

function CoreOrb() {
  applyAppearance()
  updateSleepClock()
  window.setInterval(updateSleepClock, 1000)
  window.addEventListener("pointerdown", () => {
    VoiceController.unlock()
    void SpeechInputController.resumeAudioContext()
  }, { once: true })
  window.addEventListener("keydown", () => {
    VoiceController.unlock()
    void SpeechInputController.resumeAudioContext()
  }, { once: true })
  window.addEventListener("pointerdown", () => {
    if (state.settings.coreVisual === "video" && coreVideo.paused && !state.settings.reduceMotion) {
      playCoreVideo()
    }
  }, { passive: true })
}

window.addEventListener("pagehide", () => {
  SpeechInputController.stop()
  state.calendarEvents?.close()
  state.calendarEvents = null
  if (navigator.sendBeacon) {
    navigator.sendBeacon("/ui/chat/clear")
    return
  }
  fetch("/ui/chat/clear", {
    method: "POST",
    keepalive: true,
  }).catch(() => null)
})

CoreOrb()
PromptInput()
ConnectionIndicator()
SettingsPanel()
connect()
connectCalendarEvents()
