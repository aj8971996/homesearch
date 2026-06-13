import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

function thumbUrl(url) {
  if (!url) return url
  const u = url.replace(/^http:\/\//, 'https://')
  // Ensure we always use the confirmed-working s.jpg thumbnail
  return u.endsWith('s.jpg') ? u : u.replace(/\.jpg$/, 's.jpg')
}

export default function PhotoCarousel({ photos = [], photoCount = 0, listingUrl = '', sourceLabel = 'Listing' }) {
  const [lightboxIdx, setLightboxIdx] = useState(null)

  const n     = photos.length
  const total = photoCount || n
  const isOpen = lightboxIdx !== null

  const lbPrev = (e) => { e?.stopPropagation(); setLightboxIdx(i => (i - 1 + n) % n) }
  const lbNext = (e) => { e?.stopPropagation(); setLightboxIdx(i => (i + 1) % n) }
  const close  = () => setLightboxIdx(null)

  // Lock body scroll and handle keyboard while lightbox is open
  useEffect(() => {
    if (!isOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    const onKey = (e) => {
      if (e.key === 'Escape')     { e.preventDefault(); close() }
      if (e.key === 'ArrowLeft')  { e.preventDefault(); setLightboxIdx(i => (i - 1 + n) % n) }
      if (e.key === 'ArrowRight') { e.preventDefault(); setLightboxIdx(i => (i + 1) % n) }
    }
    window.addEventListener('keydown', onKey)
    return () => {
      document.body.style.overflow = prev
      window.removeEventListener('keydown', onKey)
    }
  }, [isOpen, n])

  if (n === 0) {
    return (
      <div className="h-52 bg-pn-surface flex flex-col items-center justify-center gap-2 text-pn-muted">
        <span className="text-4xl">🏠</span>
        <span className="text-xs">No photos available</span>
      </div>
    )
  }

  return (
    <>
      {/* ── Single thumbnail ── */}
      <div
        className="relative h-52 overflow-hidden bg-pn-surface cursor-zoom-in"
        onClick={() => setLightboxIdx(0)}
      >
        <img
          src={thumbUrl(photos[0])}
          alt="Listing photo"
          className="w-full h-full object-cover"
          onError={(e) => { e.target.style.display = 'none' }}
        />
        {total > 1 && (
          <span className="absolute bottom-2 right-2 bg-black/55 backdrop-blur-sm
            text-white text-[11px] font-medium px-2.5 py-1 rounded-full pointer-events-none">
            📷 {total} photos
          </span>
        )}
        <span className="absolute top-2 right-2 bg-black/40 backdrop-blur-sm
          text-white text-[10px] px-2 py-0.5 rounded-full pointer-events-none">
          click to expand
        </span>
      </div>

      {/* ── Lightbox portal ── */}
      {isOpen && createPortal(
        <div
          className="fixed inset-0 z-[9999] bg-black flex flex-col"
          onClick={close}
        >
          {/* Header bar */}
          <div
            className="flex items-center justify-between px-5 py-3 shrink-0"
            onClick={e => e.stopPropagation()}
          >
            <span className="text-white/50 text-sm tabular-nums select-none">
              {lightboxIdx + 1} / {n}
            </span>
            {listingUrl && (
              <a
                href={listingUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-white/70 hover:text-white text-xs underline underline-offset-2"
                onClick={e => e.stopPropagation()}
              >
                View full quality on {sourceLabel} ↗
              </a>
            )}
            <button
              onClick={close}
              className="text-white/70 hover:text-white text-3xl leading-none w-10 h-10
                flex items-center justify-center"
            >
              ×
            </button>
          </div>

          {/* Image area */}
          <div className="flex-1 flex items-center justify-center relative min-h-0">
            <img
              key={lightboxIdx}
              src={thumbUrl(photos[lightboxIdx])}
              alt={`Photo ${lightboxIdx + 1} of ${n}`}
              className="max-h-full max-w-full object-contain"
              onClick={e => e.stopPropagation()}
              onError={(e) => { e.target.style.opacity = '0.2' }}
            />

            {n > 1 && (
              <>
                <button
                  onClick={lbPrev}
                  className="absolute left-4 w-12 h-12 rounded-full bg-white/10
                    hover:bg-white/25 text-white text-3xl flex items-center
                    justify-center transition-colors"
                >
                  ‹
                </button>
                <button
                  onClick={lbNext}
                  className="absolute right-4 w-12 h-12 rounded-full bg-white/10
                    hover:bg-white/25 text-white text-3xl flex items-center
                    justify-center transition-colors"
                >
                  ›
                </button>
              </>
            )}
          </div>

          {/* Dot strip */}
          {n > 1 && n <= 30 && (
            <div
              className="flex gap-1.5 justify-center py-3 shrink-0"
              onClick={e => e.stopPropagation()}
            >
              {photos.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setLightboxIdx(i)}
                  className={`w-1.5 h-1.5 rounded-full transition-all
                    ${i === lightboxIdx ? 'bg-white scale-125' : 'bg-white/30 hover:bg-white/60'}`}
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
