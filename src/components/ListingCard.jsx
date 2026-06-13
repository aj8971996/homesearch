import PhotoViewer from './PhotoViewer'
import DaysOnMarketPill from './DaysOnMarketPill'
import PriceChangePill from './PriceChangePill'

export default function ListingCard({ listing, lastRunDate }) {
  const {
    zpid, address, zipcode, rent, rent_history,
    bedrooms, bathrooms, sqft,
    days_on_market, first_seen_date,
    photo_count, listing_url, source,
  } = listing

  const SOURCE_LABELS = { zillow: 'Zillow', zillow_apilow: 'Zillow', realtor: 'Realtor.com' }
  const sourceLabel = SOURCE_LABELS[source] ?? 'Listing'

  const baths = bathrooms % 1 ? bathrooms.toFixed(1) : String(bathrooms)
  const isNew = Boolean(lastRunDate && first_seen_date === lastRunDate)

  return (
    <div className="bg-pn-surface border border-pn-border rounded-xl overflow-hidden
      shadow-card hover:-translate-y-0.5 hover:shadow-card-hover transition-all duration-200">

      <div className="p-4 flex flex-col gap-3">

        {/* Rent + status pills */}
        <div className="flex items-start justify-between gap-2">
          <div>
            <span className="text-3xl font-extrabold tracking-tight text-pn-txt">
              ${rent.toLocaleString()}
            </span>
            <span className="text-sm text-pn-muted ml-1">/mo</span>
          </div>
          <div className="flex flex-col items-end gap-1 pt-1">
            <DaysOnMarketPill daysOnMarket={days_on_market ?? 0} isNew={isNew} />
            <PriceChangePill rent={rent} rentHistory={rent_history} />
          </div>
        </div>

        {/* Address */}
        <p className="text-xs text-pn-sub flex items-start gap-1">
          <span className="mt-0.5 flex-shrink-0">📍</span>
          <span>{address}</span>
        </p>

        {/* Stats row */}
        <div className="flex items-center flex-wrap text-xs text-pn-sub">
          <Stat val={bedrooms} label="bed" />
          <Sep />
          <Stat val={baths} label="bath" />
          <Sep />
          <Stat val={sqft ? sqft.toLocaleString() : '—'} label="sq ft" />
        </div>

        {/* Amenity badges */}
        <div className="flex flex-wrap gap-1.5">
          <Badge>❄️ AC</Badge>
          <Badge>🫧 W/D In Unit</Badge>
          <Badge>🐱 Cats OK</Badge>
        </div>

        {/* Footer — photos button + listing link */}
        <div className="flex items-center justify-between gap-2 pt-1">
          <PhotoViewer
            zpid={zpid}
            photoCount={photo_count ?? 0}
            listingUrl={listing_url}
            sourceLabel={sourceLabel}
          />
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-pn-muted border border-pn-border px-2 py-0.5 rounded">
              {zipcode}
            </span>
            {listing_url && (
              <a
                href={listing_url}
                target="_blank"
                rel="noopener noreferrer"
                className="px-4 py-1.5 rounded-pill bg-pn-accent text-white text-xs font-bold
                  hover:opacity-85 transition-opacity"
              >
                View on {sourceLabel} →
              </a>
            )}
          </div>
        </div>

      </div>
    </div>
  )
}

function Stat({ val, label }) {
  return (
    <span className="flex items-baseline gap-0.5">
      <strong className="text-pn-txt font-bold">{val}</strong>
      <span>{label}</span>
    </span>
  )
}

function Sep() {
  return <span className="mx-2 text-pn-border select-none">·</span>
}

function Badge({ children }) {
  return (
    <span className="px-2.5 py-0.5 rounded-pill border border-pn-border
      text-[11px] text-pn-muted bg-pn-dim/20">
      {children}
    </span>
  )
}
