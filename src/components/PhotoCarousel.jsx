import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

// rdcpix.com CDN: stored URLs end in .jpg (unsized, may 404).
// Thumbnail: force s.jpg (confirmed working small size).
// Full-size: try x.jpg (extra large) then s.jpg fallback.
function thumbUrl(url) {
  if (!url) return url
  const u = url.replace(/^http:\/\//, 'https://')
  return u.endsWith('s.jpg') ? u : u.replace(/\.jpg$/, 's.jpg')
}

function fullUrl(url) {
  if (!url) return url
  const u = url.replace(/^http:\/\//, 'https://')
  return u.endsWith('x.jpg') ? u : u.replace(/\.jpg$/, 'x.jpg')
}

function fullFallback(src) {
  if (src.endsWith('x.jpg')) return src.replace(/x\.jpg$/, 's.jpg')
  return null
}

export default function PhotoCarousel({ photos = [], photoCount = 0 }) {
  const [lightboxIdx, setLightboxIdx] = useState(null) // null = closed
  const [lbErrors, setLbErrors]       = useState({})

  const n         = photos.length
  const total     = photoCount || n
  const isOpen    = lightboxIdx !== null

  const lbPrev = (e) => { e?.stopPropagation(); setLightboxIdx(i => (i - 1 + n) % n) }
  const lbNext = (e) => { e?.stopPropagation(); setLightboxIdx(i => (i + 1) % n) }
  const close  = ()  => { setLightboxIdx(null); setLbErrors({}) }

  useEffect(() => {
    if (!isOpen) return
    const onKey = (e) => {
      if (e.key === 'Escape')     close()
      if (e.key === 'ArrowLeft')  setLightboxIdx(i => (i - 1 + n) % n)
      if (e.key === 'ArrowRight') setLightboxIdx(i => (i + 1) % n)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
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

        {/* Photo count badge */}
        {total > 1 && (
          <span className="absolute bottom-2 right-2 bg-black/55 backdrop-blur-sm
            text-white text-[11px] font-medium px-2.5 py-1 rounded-full pointer-events-none">
            📷 {total} photos
          </span>
        )}

        {/* Expand hint */}
        <span className="absolute top-2 right-2 bg-black/40 backdrop-blur-sm
          text-white text-[10px] px-2 py-0.5 rounded-full pointer-events-none">
          click to expand
        </span>
      </div>

      {/* ── Lightbox portal ── */}
      {isOpen && createPortal(
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={close}
        >
          {/* Close */}
          <button
            onClick={close}
            className="absolute top-4 right-5 text-white/70 hover:text-white text-4xl leading-none z-10"
          >
            ×
          </button>

          {/* Counter */}
          <span className="absolute top-5 left-1/2 -translate-x-1/2 text-white/50 text-sm tabular-nums select-none">
            {lightboxIdx + 1} / {n}
          </span>

          {/* Full-size image — tries x.jpg then falls back to s.jpg */}
          <div className="flex items-center justify-center max-h-[90vh] max-w-[90vw]" onClick={e => e.stopPropagation()}>
            {lbErrors[lightboxIdx] ? (
              <span className="text-white/40 text-sm">Image unavailable</span>
            ) : (
              <img
                key={lightboxIdx}
                src={fullUrl(photos[lightboxIdx])}
                alt={`Photo ${lightboxIdx + 1} of ${n}`}
                className="max-h-[90vh] max-w-[90vw] object-contain rounded shadow-2xl"
                onError={(e) => {
                  const fallback = fullFallback(e.target.src)
                  if (fallback) {
                    e.target.src = fallback
                  } else {
                    setLbErrors(prev => ({ ...prev, [lightboxIdx]: true }))
                  }
                }}
              />
            )}
          </div>

          {/* Prev / Next */}
          {n > 1 && (
            <>
              <button
                onClick={lbPrev}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                  bg-white/10 hover:bg-white/25 text-white text-3xl flex items-center
                  justify-center transition-colors"
              >
                ‹
              </button>
              <button
                onClick={lbNext}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                  bg-white/10 hover:bg-white/25 text-white text-3xl flex items-center
                  justify-center transition-colors"
              >
                ›
              </button>
            </>
          )}

          {/* Dot strip for quick jumping */}
          {n > 1 && n <= 30 && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
              {photos.map((_, i) => (
                <button
                  key={i}
                  onClick={(e) => { e.stopPropagation(); setLightboxIdx(i) }}
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
