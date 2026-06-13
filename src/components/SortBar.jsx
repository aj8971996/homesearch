const OPTIONS = [
  { label: 'Rent ↑',   field: 'rent', dir: 'asc'  },
  { label: 'Rent ↓',   field: 'rent', dir: 'desc' },
  { label: 'Sq Ft ↑',  field: 'sqft', dir: 'asc'  },
  { label: 'Sq Ft ↓',  field: 'sqft', dir: 'desc' },
]

export default function SortBar({ sort, onSort }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      <span className="text-xs font-semibold tracking-wide text-pn-muted">Sort</span>
      {OPTIONS.map(o => {
        const active = sort.field === o.field && sort.dir === o.dir
        return (
          <button
            key={o.label}
            onClick={() => onSort({ field: o.field, dir: o.dir })}
            className={`px-3.5 py-1.5 rounded-pill text-xs border transition-all duration-150
              ${active
                ? 'bg-pn-accent border-pn-accent text-white font-bold'
                : 'bg-pn-surface border-pn-border text-pn-sub hover:border-pn-accent hover:text-pn-txt'
              }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}
