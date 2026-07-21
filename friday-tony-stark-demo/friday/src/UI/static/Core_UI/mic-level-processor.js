class FridayMicLevelProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this.energy = 0
    this.frameCount = 0
    this.reportEveryFrames = Math.max(1, Math.round(sampleRate * 0.04))
  }

  process(inputs) {
    const channels = inputs[0]
    const sampleCount = channels?.[0]?.length || 0
    if (!sampleCount) return true

    for (let frame = 0; frame < sampleCount; frame += 1) {
      let frameEnergy = 0
      for (const channel of channels) {
        const sample = channel[frame] || 0
        frameEnergy += sample * sample
      }
      this.energy += frameEnergy / channels.length
    }
    this.frameCount += sampleCount

    if (this.frameCount >= this.reportEveryFrames) {
      this.port.postMessage({ rms: Math.sqrt(this.energy / this.frameCount) })
      this.energy = 0
      this.frameCount = 0
    }
    return true
  }
}

registerProcessor("friday-mic-level", FridayMicLevelProcessor)
