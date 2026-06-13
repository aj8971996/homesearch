import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

const BASE = import.meta.env.BASE_URL

export default function PhotoViewer({ zpid, photoCount = 0, listingUrl = '', sourceLabel = 'Listing' }) {
  const [state, setState]     = useState('idle')   // idle | loading | ready | error
  const [photos, setPhotos]   = useState([])
  const [idx, setIdx]         = useState(0)
  const isOpen = state === 'ready'

  const open = async () => {
    if (state === 'ready') { setState('ready'); return }
    setState('loading')
    try {
      const res = await fetch(`${BASE}data/photos/${zpid}.json`)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()
      setPhotos(data.photos ?? [])
      setIdx(0)
      setState('ready')
    } catch {
      setState('error')
    }
  }

  const close = () => setState('idle')
  const prev  = (e) => { e?.stopPropagation(); setIdx(i => (i - 1 + photos.length) % photos.length) }
  const next  = (e) => { e?.stopPropagation(); setIdx(i => (i + 1) % photos.length) }

  useEffect(() => {
    if (!isOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e) => {
      if (e.key === 'Escape')     { e.preventDefault(); close() }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); setIdx(i => (i - 1 + photos.length) % photos.length) }
      if (e.key === 'ArrowRight') { e.preventDefault(); setIdx(i => (i + 1) % photos.length) }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [isOpen, photos.length])

  const n = photos.length

  return (
    <>
      <button
        onClick={open}
        disabled={state === 'loading' || photoCount === 0}
        className="flex items-center gap-2 px-4 py-1.5 rounded-pill border border-pn-border
          text-xs font-semibold text-pn-sub hover:border-pn-accent hover:text-pn-accent
          transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
      >
        {state === 'loading' ? (
          <>⏳ Loading…</>
        ) : state === 'error' ? (
          <>⚠ Photos unavailable</>
        ) : (
          <>📷 {photoCount > 0 ? `${photoCount} photos` : 'No photos'}</>
        )}
      </button>

      {isOpen && createPortal(
        <div className="fixed inset-0 z-[9999] bg-black flex flex-col" onClick={close}>

          {/* Header */}
          <div
            className="flex items-center justify-between px-5 py-3 shrink-0 border-b border-white/10"
            onClick={e => e.stopPropagation()}
          >
            <span className="text-white/50 text-sm tabular-nums select-none">
              {n > 0 ? `${idx + 1} / ${n}` : ''}
            </span>
            {listingUrl && (
              <a
                href={listingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-white/60 hover:text-white text-xs underline underline-offset-2"
                onClick={e => e.stopPropagation()}
              >
                View on {sourceLabel} ↗
              </a>
            )}
            <button
              onClick={close}
              className="text-white/60 hover:text-white text-3xl leading-none w-10 h-10
                flex items-center justify-center"
            >
              ×
            </button>
          </div>

          {/* Image */}
          <div className="flex-1 flex items-center justify-center relative min-h-0">
            {n === 0 ? (
              <span className="text-white/40 text-sm">No photos available</span>
            ) : (
              <img
                key={idx}
                src={photos[idx]}
                alt={`Photo ${idx + 1} of ${n}`}
                className="max-h-full max-w-full object-contain"
                onClick={e => e.stopPropagation()}
                onError={(e) => { e.target.style.opacity = '0.15' }}
              />
            )}

            {n > 1 && (
              <>
                <button onClick={prev}
                  className="absolute left-4 w-12 h-12 rounded-full bg-white/10
                    hover:bg-white/25 text-white text-3xl flex items-center justify-center transition-colors">
                  ‹
                </button>
                <button onClick={next}
                  className="absolute right-4 w-12 h-12 rounded-full bg-white/10
                    hover:bg-white/25 text-white text-3xl flex items-center justify-center transition-colors">
                  ›
                </button>
              </>
            )}
          </div>

          {/* Dot strip */}
          {n > 1 && n <= 40 && (
            <div
              className="flex gap-1 justify-center py-3 shrink-0 flex-wrap px-4"
              onClick={e => e.stopPropagation()}
            >
              {photos.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setIdx(i)}
                  className={`w-1.5 h-1.5 rounded-full transition-all
                    ${i === idx ? 'bg-white scale-125' : 'bg-white/30 hover:bg-white/60'}`}
                />
              ))}
            </div>
          )}
        </div>,
        document.body
      )}
    </>
  )
}
