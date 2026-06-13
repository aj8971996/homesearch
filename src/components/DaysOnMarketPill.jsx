export default function DaysOnMarketPill({ daysOnMarket, isNew }) {
  if (isNew) {
    return (
      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-pill
        text-[10px] font-bold tracking-wide bg-pn-accent text-white shadow-sm">
        ✦ New
      </span>
    )
  }
  return (
    <span className="inline-flex items-center px-2.5 py-0.5 rounded-pill
      text-[10px] font-semibold bg-black/60 text-white/85
      border border-white/10 backdrop-blur-sm">
      {daysOnMarket} day{daysOnMarket !== 1 ? 's' : ''} on market
    </span>
  )
}
