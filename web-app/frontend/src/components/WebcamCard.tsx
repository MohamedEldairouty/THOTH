import { useEffect, useRef, useState } from 'react'
import { analyzeVisionFrame, getVisionEnabled, type VisionProfile } from '../services/api'
import { useLanguage } from '../hooks/useLanguage'

/**
 * Floating webcam preview card for the chat page.
 *
 * Privacy: camera is OFF by default. The visitor must explicitly click
 * "Enable camera" — that single click both requests permission AND opts
 * them in to the tone-adaptive vision pipeline.
 *
 * When active:
 *   - small live preview (mirrored, like a selfie)
 *   - grabs a JPEG every 3 s and POSTs to /api/vision/analyze
 *   - shows the latest age / mood chip (or "—" if no face)
 *   - pauses polling when the tab is hidden
 *   - red recording dot + 1-click off
 *
 * The whole component renders nothing structural if disabled — it's just
 * a button until the visitor opts in.
 */

const T = {
  en: {
    enable: 'Enable camera',
    disable: 'Turn off',
    privacy: 'Camera off — your face is never stored.',
    activeHint: 'Live · used to adapt THOTH’s tone',
    noFace: 'No face detected',
    looking: 'Looking…',
    lock: 'Lock reading',
    unlock: 'Unlock',
    locked: 'LOCKED',
    disabledTitle: 'Vision temporarily disabled',
    disabledBody: 'Tone-adaptive vision is paused on this kiosk. THOTH still answers normally — just without the mood / age cues.',
  },
  ar: {
    enable: 'تفعيل الكاميرا',
    disable: 'إيقاف',
    privacy: 'الكاميرا مغلقة — لا يتم حفظ صورتك أبدًا.',
    activeHint: 'مباشر · يُستخدم لتكييف نبرة تحوت',
    noFace: 'لم يتم اكتشاف وجه',
    looking: 'جارٍ النظر…',
    lock: 'تثبيت القراءة',
    unlock: 'إلغاء التثبيت',
    locked: 'مثبّت',
    disabledTitle: 'الرؤية معطّلة مؤقتًا',
    disabledBody: 'تكييف النبرة باستخدام الرؤية موقوف حاليًا على هذا الجهاز. سيستمر تحوت في الإجابة بشكل طبيعي بدون قراءة المزاج أو العمر.',
  },
  fr: {
    enable: 'Activer la caméra',
    disable: 'Désactiver',
    privacy: 'Caméra désactivée — votre visage n’est jamais enregistré.',
    activeHint: 'En direct · adapte le ton de THOTH',
    noFace: 'Aucun visage détecté',
    looking: 'Analyse…',
    lock: 'Verrouiller',
    unlock: 'Déverrouiller',
    locked: 'VERROUILLÉ',
    disabledTitle: 'Vision temporairement désactivée',
    disabledBody: 'L’adaptation du ton par la vision est suspendue sur cette borne. THOTH répond normalement — simplement sans détecter l’humeur ou l’âge.',
  },
}

const MOOD_LABEL: Record<string, { en: string; ar: string; fr: string; emoji: string }> = {
  happy:    { en: 'Happy',    ar: 'سعيد',    fr: 'Heureux',   emoji: '😊' },
  sad:      { en: 'Sad',      ar: 'حزين',    fr: 'Triste',    emoji: '😔' },
  angry:    { en: 'Angry',    ar: 'غاضب',    fr: 'En colère', emoji: '😠' },
  fear:     { en: 'Anxious',  ar: 'قلق',     fr: 'Anxieux',   emoji: '😟' },
  surprise: { en: 'Surprised',ar: 'متفاجئ',  fr: 'Surpris',   emoji: '😮' },
  disgust:  { en: 'Disgust',  ar: 'اشمئزاز', fr: 'Dégoût',    emoji: '😖' },
  neutral:  { en: 'Neutral',  ar: 'حيادي',   fr: 'Neutre',    emoji: '😐' },
}

const AGE_LABEL: Record<string, { en: string; ar: string; fr: string }> = {
  child:  { en: 'Child',     ar: 'طفل',  fr: 'Enfant' },
  teen:   { en: 'Teen',      ar: 'مراهق', fr: 'Ado' },
  adult:  { en: 'Adult',     ar: 'بالغ', fr: 'Adulte' },
  senior: { en: 'Older adult', ar: 'مسنّ', fr: 'Senior' },
}

// Demo-tuned: 8s gives the presenter time to pose, see the chip lock in,
// point at it, and send the chat message before the next capture might
// flip it. Backend chat handler reads from the 15s cache, so the prediction
// you saw is still the one Gemini gets even if you take a few seconds.
const POLL_MS = 8000
const CAPTURE_W = 320  // small frame = fast network + less compute
const CAPTURE_H = 240

export default function WebcamCard() {
  const { lang } = useLanguage()
  const t = T[lang]

  const [enabled, setEnabled] = useState(false)
  const [profile, setProfile] = useState<VisionProfile | null>(null)
  const [error, setError] = useState<string | null>(null)
  // Backend-side global kill switch (VISION_ENABLED=false in .env).
  // null = still probing on mount. Once known we either show the normal
  // camera UI or a friendly "temporarily disabled" panel.
  const [serverEnabled, setServerEnabled] = useState<boolean | null>(null)

  useEffect(() => {
    let alive = true
    getVisionEnabled().then(ok => { if (alive) setServerEnabled(ok) })
    return () => { alive = false }
  }, [])
  // Locked = stop capturing frames. The last good profile sticks on the
  // chip AND in the backend cache (we periodically re-POST the frozen
  // frame so the backend's profile TTL stays warm during a long demo
  // pause). This is the single most important demo affordance.
  const [locked, setLocked] = useState(false)
  const lastFrameRef = useRef<Blob | null>(null)

  const videoRef  = useRef<HTMLVideoElement | null>(null)
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const inflightRef = useRef(false)

  // ── Start / stop camera ────────────────────────────────────────────
  const stop = () => {
    streamRef.current?.getTracks().forEach(t => t.stop())
    streamRef.current = null
    if (videoRef.current) videoRef.current.srcObject = null
    setEnabled(false)
    setProfile(null)
    setLocked(false)
    lastFrameRef.current = null
  }

  const start = async () => {
    setError(null)
    try {
      // Use `ideal` not `exact` — iPhone Safari rejects strict tiny sizes,
      // and on most iPhones the front cam minimum is 640×480 anyway. We
      // downscale to 320×240 when we draw the frame to canvas, so the
      // actual sensor resolution doesn't matter for network/inference cost.
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width:  { ideal: 640 },
          height: { ideal: 480 },
          facingMode: 'user',
        },
        audio: false,
      })
      streamRef.current = stream
      // NOTE: don't touch videoRef here — the <video> element doesn't exist
      // until after setEnabled(true) re-renders. The effect below picks up
      // the stream once the element mounts.
      setEnabled(true)
    } catch (e: any) {
      setError(e?.name === 'NotAllowedError' ? 'permission' : 'unavailable')
      stop()
    }
  }

  // Attach the captured stream to the <video> element after it mounts.
  // Re-runs when `enabled` flips to true; the video element only exists then.
  useEffect(() => {
    if (!enabled) return
    const video = videoRef.current
    const stream = streamRef.current
    if (!video || !stream) return
    video.srcObject = stream
    video.play().catch(() => {})
  }, [enabled])

  // Clean up on unmount
  useEffect(() => () => stop(), [])

  // ── Capture loop ───────────────────────────────────────────────────
  useEffect(() => {
    if (!enabled) return
    let cancelled = false

    const tick = async () => {
      if (cancelled) return
      if (document.hidden) return
      if (inflightRef.current) return

      let blob: Blob | null = null

      if (locked) {
        // Reuse the last captured frame — keeps the backend cache fresh so
        // when the visitor finally sends a chat message, the persona_hint
        // is still based on the pose they locked in, even if minutes pass.
        blob = lastFrameRef.current
        if (!blob) return  // never locked anything yet (shouldn't happen)
      } else {
        // Capture a fresh frame from the live video.
        const video = videoRef.current
        if (!video || video.readyState < 2 || video.videoWidth === 0) return

        if (!canvasRef.current) {
          const c = document.createElement('canvas')
          c.width = CAPTURE_W
          c.height = CAPTURE_H
          canvasRef.current = c
        }
        const ctx = canvasRef.current.getContext('2d')
        if (!ctx) return
        ctx.drawImage(video, 0, 0, CAPTURE_W, CAPTURE_H)

        blob = await new Promise<Blob | null>(res =>
          canvasRef.current!.toBlob(b => res(b), 'image/jpeg', 0.7),
        )
        if (!blob) return
        lastFrameRef.current = blob
      }

      inflightRef.current = true
      try {
        const p = await analyzeVisionFrame(blob)
        if (cancelled) return
        // Sticky chip: if the new frame had no face (blink, motion blur,
        // partial out-of-frame), keep showing the last good reading rather
        // than flashing to "No face detected". The backend's profile cache
        // still respects its TTL, so the chat path won't use stale data —
        // this is purely a UI smoothing for the demo.
        if (p.face_detected) {
          setProfile(p)
        } else {
          setProfile(prev => prev?.face_detected ? prev : p)
        }
      } catch {
        // Swallow — single failures shouldn't kill the loop. The chip
        // just keeps showing whatever the last good profile was.
      } finally {
        inflightRef.current = false
      }
    }

    // Fire once immediately so the chip populates fast, then on interval.
    tick()
    const id = window.setInterval(tick, POLL_MS)
    return () => { cancelled = true; window.clearInterval(id) }
    // `locked` must be in the deps: when the user locks, we tear down this
    // loop and start a new one that re-POSTs the frozen frame instead of
    // capturing fresh ones. (Including `locked` here also keeps the closure
    // reading the current value instead of the stale one.)
  }, [enabled, locked])

  // ── Server-side disabled: show a friendly notice instead of the
  //    Enable button. Camera UI stays visible (so audience/judges can
  //    see the feature exists) but explicitly off.
  if (serverEnabled === false) {
    return (
      <div className="gem-card p-3 flex flex-col gap-2 border-gem-gold/15 opacity-70">
        <div className="flex items-center gap-2">
          <span className="text-base">📷</span>
          <span className="text-xs font-display text-gem-gold">
            {t.disabledTitle}
          </span>
        </div>
        <p className="text-gem-muted/70 text-[10px] leading-snug">
          {t.disabledBody}
        </p>
      </div>
    )
  }

  // Probe in flight — render nothing structural to avoid flicker. The
  // card has a min-height naturally from gem-card padding.
  if (serverEnabled === null) {
    return <div className="gem-card p-3 border-gem-gold/15 opacity-50" />
  }

  // ── Off state: just the enable button ──────────────────────────────
  if (!enabled) {
    return (
      <div className="gem-card p-3 flex flex-col gap-2 border-gem-gold/20">
        <button
          onClick={start}
          className="gem-btn-primary text-xs py-1.5 px-3"
        >
          📷 {t.enable}
        </button>
        <p className="text-gem-muted/60 text-[10px] leading-tight">
          {error === 'permission'
            ? (lang === 'ar' ? 'تم رفض الإذن. افتح إعدادات الموقع وفعّل الكاميرا.' :
               lang === 'fr' ? 'Autorisation refusée. Activez la caméra dans les réglages du site.' :
               'Permission denied. Allow camera in site settings to enable.')
            : error === 'unavailable'
            ? (lang === 'ar' ? 'الكاميرا غير متاحة.' : lang === 'fr' ? 'Caméra indisponible.' : 'Camera unavailable.')
            : t.privacy}
        </p>
      </div>
    )
  }

  // ── On state: preview + chip + off ─────────────────────────────────
  const moodMeta  = profile?.mood     ? MOOD_LABEL[profile.mood]      : null
  const ageMeta   = profile?.age_group ? AGE_LABEL[profile.age_group] : null
  const hasFace   = !!profile?.face_detected
  const moodLabel = moodMeta ? `${moodMeta.emoji} ${moodMeta[lang]}` : null
  const ageLabel  = ageMeta  ? ageMeta[lang]                          : null

  return (
    <div className="gem-card p-3 flex flex-col gap-2 border-gem-gold/30">
      <div className="relative">
        <video
          ref={videoRef}
          muted
          autoPlay
          playsInline
          // iOS Safari needs the legacy lowercase attribute too. Without
          // it the video tries to enter fullscreen on play(), which fails
          // silently in a non-gesture context and leaves the element black.
          {...{ 'webkit-playsinline': 'true' }}
          className="w-full rounded-lg bg-black/40"
          style={{ aspectRatio: '4 / 3', transform: 'scaleX(-1)' }}
        />
        {/* Status indicator — red when live, amber when locked */}
        <span className="absolute top-1.5 left-1.5 flex items-center gap-1 bg-black/60 backdrop-blur-sm px-1.5 py-0.5 rounded-full text-[10px] text-white">
          {locked ? (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
              🔒 {t.locked}
            </>
          ) : (
            <>
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              LIVE
            </>
          )}
        </span>
      </div>

      {/* Live chip */}
      <div className="text-xs flex items-center gap-2 flex-wrap min-h-[1.5rem]">
        {!profile ? (
          <span className="text-gem-muted/60 italic">{t.looking}</span>
        ) : !hasFace ? (
          <span className="text-gem-muted/60">— {t.noFace}</span>
        ) : (
          <>
            {moodLabel && (
              <span className="bg-gem-gold/10 border border-gem-gold/30 rounded-full px-2 py-0.5 text-gem-text">
                {moodLabel}
              </span>
            )}
            {ageLabel && (
              <span className="bg-gem-gold/10 border border-gem-gold/30 rounded-full px-2 py-0.5 text-gem-text">
                {ageLabel}
              </span>
            )}
          </>
        )}
      </div>

      <p className="text-gem-muted/60 text-[10px] leading-tight">
        {t.activeHint}
      </p>

      {/* Lock / unlock — the demo-critical button. Locking freezes the chip
          AND keeps re-POSTing the last frame so the backend cache stays
          warm while you compose the chat message. */}
      <button
        onClick={() => setLocked(v => !v)}
        disabled={!profile?.face_detected && !locked}
        className={`text-[11px] py-1 px-2 rounded transition-colors disabled:opacity-40 ${
          locked
            ? 'bg-amber-500/20 border border-amber-400/50 text-amber-200 hover:bg-amber-500/30'
            : 'bg-gem-gold/10 border border-gem-gold/30 text-gem-gold hover:bg-gem-gold/20'
        }`}
      >
        {locked ? `🔓 ${t.unlock}` : `🔒 ${t.lock}`}
      </button>

      <button
        onClick={stop}
        className="text-gem-gold/70 hover:text-gem-gold text-[11px] underline self-start transition-colors"
      >
        {t.disable}
      </button>
    </div>
  )
}
