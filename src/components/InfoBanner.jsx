export default function InfoBanner({ meta, visibleCount }) {
  const lastUpdated = meta?.last_updated
    ? new Date(meta.last_updated).toLocaleDateString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
      })
    : 'Pending first run'

  return (
    <div className="bg-pn-surface border border-pn-border rounded-xl p-6 mt-6 mb-5">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-3">
        <h1 className="text-2xl font-extrabold tracking-tight">
          Las Vegas <span className="text-pn-accent">Home Search</span>
        </h1>
        <div className="flex flex-wrap gap-2">
          <Chip>{visibleCount} active listing{visibleCount !== 1 ? 's' : ''}</Chip>
          <Chip>Last refresh: {lastUpdated}</Chip>
          <Chip>Refreshes every 3 days</Chip>
        </div>
      </div>

      <p className="text-xs text-pn-muted leading-relaxed max-w-3xl mb-3">
        A personal family home search tool for West Las Vegas. Every listing shown already
        qualifies — 3+ bedrooms, 2+ bathrooms, 1,300+&nbsp;sq&nbsp;ft, ≤&nbsp;$2,500/mo,
        with AC, washer/dryer in unit, and cats OK. No manual filtering needed.
      </p>

      <div className="flex flex-wrap gap-5">
        <MetaTag label="Source"    value="Zillow via OpenWebNinja API" />
        <MetaTag label="Zip codes" value="89134 · 89144 · 89145 · 89128 · 89138 · 89135" />
        <MetaTag label="Cadence"   value="Every 3 days · free API tier" />
      </div>
    </div>
  )
}

function Chip({ children }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill
      bg-pn-dim/30 border border-pn-border text-xs text-pn-sub whitespace-nowrap">
      <span className="w-1.5 h-1.5 rounded-full bg-pn-accent flex-shrink-0" />
      {children}
    </span>
  )
}

function MetaTag({ label, value }) {
  return (
    <span className="text-xs text-pn-muted flex items-center gap-1 flex-wrap">
      {label}:&nbsp;<span className="text-pn-accent font-semibold">{value}</span>
    </span>
  )
}
