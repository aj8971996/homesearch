const OPTIONS = [
  { val: 'all',       label: 'Both'         },
  { val: 'HOUSE',     label: '🏠 Houses'   },
  { val: 'TOWNHOUSE', label: '🏘 Townhomes' },
]

export default function PropertyTypeRadio({ value, onChange }) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-pn-muted">Type</span>
      <div className="flex">
        {OPTIONS.map((o, i) => {
          const active   = value === o.val
          const isFirst  = i === 0
          const isLast   = i === OPTIONS.length - 1
          return (
            <button
              key={o.val}
              onClick={() => onChange(o.val)}
              className={`px-3.5 py-1.5 text-xs border transition-all duration-150 -ml-px first:ml-0
                ${isFirst ? 'rounded-l-pill' : ''} ${isLast ? 'rounded-r-pill' : ''}
                ${active
                  ? 'bg-pn-accent border-pn-accent text-white font-bold z-10'
                  : 'bg-pn-surface border-pn-border text-pn-sub hover:border-pn-accent hover:text-pn-txt'
                }`}
            >
              {o.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
