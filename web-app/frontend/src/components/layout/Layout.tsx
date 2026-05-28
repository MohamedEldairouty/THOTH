import { useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'

// 32-byte silent WAV — tiny payload, all browsers decode it.
// Used to prime mobile autoplay (iOS Safari) on the user's first tap.
const SILENT_WAV =
  'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAVFYAAFRWAAABAAgAZGF0YQAAAAA='

let audioUnlocked = false

/** Plays a silent audio inside a user-gesture handler. After this call
 *  succeeds once, iOS Safari permits programmatic Audio.play() across
 *  every other element on the page for the rest of the session. */
function unlockAudio() {
  if (audioUnlocked) return
  audioUnlocked = true
  const el = new Audio(SILENT_WAV)
  el.muted = true
  el.play().then(() => {
    el.pause()
    el.muted = false
  }).catch(() => {
    // Tap was too quick or browser refused — try again on next tap
    audioUnlocked = false
  })
}

export default function Layout() {
  useEffect(() => {
    // Capture the FIRST tap anywhere in the app and use it to unlock audio.
    // Without this, the chat greeting / tour narrations / nav narrations
    // can't autoplay on iOS because the gesture chain is broken by the
    // async fetch that produces the audio.
    const handler = () => unlockAudio()
    document.addEventListener('pointerdown', handler, { capture: true })
    document.addEventListener('touchstart',  handler, { capture: true, passive: true })
    return () => {
      document.removeEventListener('pointerdown', handler, { capture: true } as any)
      document.removeEventListener('touchstart',  handler, { capture: true } as any)
    }
  }, [])

  return (
    <div className="min-h-screen bg-gem-navy flex flex-col">
      <Navbar />
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}
