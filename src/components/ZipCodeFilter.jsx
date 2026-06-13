export default function ZipCodeFilter({ selected, onChange, zips }) {
  if (zips.length === 0) return null

  const toggle = (zip) =>
    onChange(selected.includes(zip) ? selected.filter(z => z !== zip) : [...selected, zip])

  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs text-pn-muted">Zip</span>
      <div className="flex flex-wrap gap-1">
        {zips.map(zip => {
          const active = selected.includes(zip)
          return (
            <button
              key={zip}
              onClick={() => toggle(zip)}
              className={`px-3 py-1.5 text-xs border rounded-pill transition-all duration-150
                ${active
                  ? 'bg-pn-accent border-pn-accent text-white font-bold'
                  : 'bg-pn-surface border-pn-border text-pn-sub hover:border-pn-accent hover:text-pn-txt'
                }`}
            >
              {zip}
            </button>
          )
        })}
        {selected.length > 0 && (
          <button
            onClick={() => onChange([])}
            className="px-3 py-1.5 text-xs border rounded-pill border-pn-border
              text-pn-muted hover:border-pn-accent hover:text-pn-txt transition-all duration-150"
          >
            Clear
          </button>
        )}
      </div>
    </div>
  )
}
