import { useState } from 'react'

export default function PhotoCarousel({ photos = [], photoCount = 0 }) {
  const [idx, setIdx]       = useState(0)
  const [errors, setErrors] = useState({})

  const n = photos.length

  if (n === 0) {
    return (
      <div className="h-52 bg-pn-surface flex flex-col items-center justify-center gap-2 text-pn-muted">
        <span className="text-4xl">🏠</span>
        <span className="text-xs">No photos available</span>
      </div>
    )
  }

  const prev = () => setIdx(i => (i - 1 + n) % n)
  const next = () => setIdx(i => (i + 1) % n)
  const markError = i => setErrors(e => ({ ...e, [i]: true }))

  // Cap dots at 8 to avoid overcrowding
  const dotCount = Math.min(n, 8)

  return (
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
              src={url}
              alt={`Photo ${i + 1} of ${photoCount || n}`}
              className="w-full h-full object-cover"
              onError={() => markError(i)}
            />
          )}
        </div>
      ))}

      {n > 1 && (
        <>
          <button
            onClick={prev}
            className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
              bg-black/55 text-white flex items-center justify-center text-lg
              hover:bg-black/80 transition-colors z-10"
          >
            ‹
          </button>
          <button
            onClick={next}
            className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full
              bg-black/55 text-white flex items-center justify-center text-lg
              hover:bg-black/80 transition-colors z-10"
          >
            ›
          </button>

          <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1.5 z-10">
            {Array.from({ length: dotCount }, (_, i) => (
              <button
                key={i}
                onClick={() => setIdx(i)}
                className={`w-1.5 h-1.5 rounded-full transition-all
                  ${i === idx ? 'bg-white scale-125' : 'bg-white/40 hover:bg-white/70'}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
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
