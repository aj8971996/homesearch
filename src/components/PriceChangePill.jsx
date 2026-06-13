export default function PriceChangePill({ rent, rentHistory }) {
  if (!rentHistory?.length) return null

  const prev  = rentHistory[0].rent
  const delta = rent - prev
  if (delta === 0) return null

  const isUp = delta > 0
  const amt  = Math.abs(delta).toLocaleString()

  return (
    <span className={`inline-flex items-center gap-0.5 px-2.5 py-0.5 rounded-pill
      text-[10px] font-bold backdrop-blur-sm shadow-sm
      ${isUp ? 'bg-red-500/90 text-white' : 'bg-green-500/90 text-white'}`}>
      {isUp ? `↑ Up $${amt}/mo` : `↓ Down $${amt}/mo`}
    </span>
  )
}
