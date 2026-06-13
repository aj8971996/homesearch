import { useState, useEffect } from 'react'
import { createPortal } from 'react-dom'

function normalizeUrl(url) {
  return url ? url.replace(/^http:\/\//, 'https://') : url
}

function imgErrorHandler(e) {
  const src = e.target.src
  if (!src.endsWith('s.jpg') && src.endsWith('.jpg')) {
    e.target.src = src.slice(0, -4) + 's.jpg'
  } else {
    e.target.style.display = 'none'
  }
}

export default function PhotoCarousel({ photos = [], photoCount = 0 }) {
  const [idx, setIdx]         = useState(0)
  const [errors, setErrors]   = useState({})
  const [lightbox, setLightbox] = useState(false)

  const n = photos.length
  const prev = (e) => { e?.stopPropagation(); setIdx(i => (i - 1 + n) % n) }
  const next = (e) => { e?.stopPropagation(); setIdx(i => (i + 1) % n) }
  const markError = i => setErrors(e => ({ ...e, [i]: true }))

  useEffect(() => {
    if (!lightbox) return
    const onKey = (e) => {
      if (e.key === 'Escape')      setLightbox(false)
      if (e.key === 'ArrowLeft')   setIdx(i => (i - 1 + n) % n)
      if (e.key === 'ArrowRight')  setIdx(i => (i + 1) % n)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [lightbox, n])

  const dotCount = Math.min(n, 8)

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
      {/* ── Carousel strip ── */}
      <div className="relative h-52 overflow-hidden bg-pn-surface select-none">
        {photos.map((url, i) => (
          <div
            key={i}
            className={`absolute inset-0 transition-opacity duration-300 ${i === idx ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
          >
            {errors[i] || !url ? (
              <Placeholder num={i + 1} total={photoCount || n} />
            ) : (
              <img
                src={normalizeUrl(url)}
                alt={`Photo ${i + 1} of ${photoCount || n}`}
                className="w-full h-full object-cover cursor-zoom-in"
                onClick={() => setLightbox(true)}
                onError={(e) => {
                  const src = e.target.src
                  if (!src.endsWith('s.jpg') && src.endsWith('.jpg')) {
                    e.target.src = src.slice(0, -4) + 's.jpg'
                  } else {
                    markError(i)
                  }
                }}
              />
            )}
          </div>
        ))}

        {n > 1 && (
          <>
            <button onClick={prev}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
                bg-black/55 text-white flex items-center justify-center text-lg
                hover:bg-black/80 transition-colors z-10">
              ‹
            </button>
            <button onClick={next}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
                bg-black/55 text-white flex items-center justify-center text-lg
                hover:bg-black/80 transition-colors z-10">
              ›
            </button>
            <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
              {Array.from({ length: dotCount }, (_, i) => (
                <button key={i} onClick={(e) => { e.stopPropagation(); setIdx(i) }}
                  className={`w-1.5 h-1.5 rounded-full transition-all
                    ${i === idx ? 'bg-white scale-125' : 'bg-white/40 hover:bg-white/70'}`}
                />
              ))}
            </div>
          </>
        )}

        {/* Click hint */}
        <div className="absolute top-2 right-2 z-10 bg-black/40 text-white text-[10px]
          px-2 py-0.5 rounded-full pointer-events-none backdrop-blur-sm">
          click to expand
        </div>
      </div>

      {/* ── Lightbox portal ── */}
      {lightbox && createPortal(
        <div
          className="fixed inset-0 z-50 bg-black/95 flex items-center justify-center"
          onClick={() => setLightbox(false)}
        >
          {/* Close */}
          <button
            onClick={() => setLightbox(false)}
            className="absolute top-4 right-5 text-white/80 hover:text-white text-4xl leading-none z-10"
          >
            ×
          </button>

          {/* Counter */}
          <span className="absolute top-5 left-1/2 -translate-x-1/2 text-white/60 text-sm tabular-nums">
            {idx + 1} / {n}
          </span>

          {/* Image */}
          <img
            src={normalizeUrl(photos[idx])}
            alt={`Photo ${idx + 1} of ${n}`}
            className="max-h-[90vh] max-w-[90vw] object-contain rounded shadow-2xl"
            onClick={(e) => e.stopPropagation()}
            onError={imgErrorHandler}
          />

          {/* Prev / Next */}
          {n > 1 && (
            <>
              <button
                onClick={prev}
                className="absolute left-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                  bg-white/10 hover:bg-white/25 text-white text-3xl flex items-center justify-center
                  transition-colors"
              >
                ‹
              </button>
              <button
                onClick={next}
                className="absolute right-4 top-1/2 -translate-y-1/2 w-12 h-12 rounded-full
                  bg-white/10 hover:bg-white/25 text-white text-3xl flex items-center justify-center
                  transition-colors"
              >
                ›
              </button>
            </>
          )}
        </div>,
        document.body
      )}
    </>
  )
}

function Placeholder({ num, total }) {
  return (
    <div className="w-full h-full flex flex-col items-center justify-center gap-2
      bg-gradient-to-br from-pn-surface to-pn-bg">
      <span className="text-4xl">🏠</span>
      <span className="text-xs text-pn-sub bg-black/30 px-3 py-1 rounded-pill backdrop-blur-sm">
        Photo {num} of {total}
      </span>
    </div>
  )
}
