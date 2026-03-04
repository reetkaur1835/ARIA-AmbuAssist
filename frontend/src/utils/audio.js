/**
 * TTS audio player with interrupt support.
 *
 * Usage:
 *   const ctrl = playAudio(base64, onStart, onEnd)
 *   ctrl.stop()   ← immediately stops playback and resolves the promise
 */

let _current = null   // { audio: HTMLAudioElement, stop: fn }

/** Stop whatever is currently playing (no-op if silent). */
export function stopAudio() {
  if (_current) {
    _current.stop()
    _current = null
  }
}

/** Returns true if TTS audio is currently playing. */
export function isAudioPlaying() {
  return _current !== null
}

/**
 * Play base64-encoded MP3.
 * Returns an object { promise, stop } so callers can await completion OR
 * imperatively stop playback.
 */
export function playAudio(base64Mp3, onStart, onEnd) {
  if (!base64Mp3) return { promise: Promise.resolve(), stop: () => {} }

  // Interrupt any currently playing audio first
  stopAudio()

  let resolveFn
  const promise = new Promise((resolve) => { resolveFn = resolve })

  const audio = new Audio(`data:audio/mpeg;base64,${base64Mp3}`)

  const finish = (interrupted = false) => {
    _current = null
    onEnd?.(interrupted)
    resolveFn()
  }

  audio.onplay  = () => onStart?.()
  audio.onended = () => finish(false)
  audio.onerror = () => finish(false)
  audio.play().catch(() => finish(false))

  const ctrl = {
    promise,
    stop: () => {
      try { audio.pause(); audio.src = '' } catch {}
      finish(true)
    },
  }

  _current = ctrl
  return ctrl
}
