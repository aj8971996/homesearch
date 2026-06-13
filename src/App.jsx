import { useState, useEffect } from 'react'
import InfoBanner from './components/InfoBanner'
import SortBar from './components/SortBar'
import PhotoFilterRadio from './components/PhotoFilterRadio'
import PropertyTypeRadio from './components/PropertyTypeRadio'
import ZipCodeFilter from './components/ZipCodeFilter'
import ListingCard from './components/ListingCard'

const BASE = import.meta.env.BASE_URL

export default function App() {
  const [listings, setListings] = useState([])
  const [meta, setMeta]         = useState(null)
  const [sort, setSort]               = useState({ field: 'rent', dir: 'asc' })
  const [photoFilter, setPhotoFilter] = useState('all')
  const [typeFilter, setTypeFilter]   = useState('all')
  const [zipFilter, setZipFilter]     = useState([])
  const [status, setStatus]     = useState('loading') // loading | ok | error

  useEffect(() => {
    Promise.all([
      fetch(`${BASE}data/listings.json`).then(r => r.json()),
      fetch(`${BASE}data/meta.json`).then(r => r.json()),
    ])
      .then(([listData, metaData]) => {
        setListings(listData.listings ?? [])
        setMeta(metaData)
        setStatus('ok')
      })
      .catch(() => setStatus('error'))
  }, [])

  const lastRunDate = meta?.last_updated?.split('T')[0] ?? null

  const availableZips = [...new Set(
    listings.filter(l => l.available).map(l => l.zipcode).filter(Boolean)
  )].sort()

  const visible = listings
    .filter(l => l.available)
    .filter(l => typeFilter === 'all' || (l.home_type ?? 'HOUSE') === typeFilter)
    .filter(l => photoFilter === 'all' || (l.photo_count ?? l.photos?.length ?? 0) >= 20)
    .filter(l => zipFilter.length === 0 || zipFilter.includes(l.zipcode))
    .sort((a, b) => {
      const [va, vb] = sort.field === 'rent'
        ? [a.rent, b.rent]
        : [a.sqft, b.sqft]
      return sort.dir === 'asc' ? va - vb : vb - va
    })

  return (
    <div className="min-h-screen bg-pn-bg text-pn-txt">
      <div className="max-w-6xl mx-auto px-4 pb-16">
        <InfoBanner meta={meta} visibleCount={visible.length} />

        <div className="flex flex-col gap-3 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <SortBar sort={sort} onSort={setSort} />
            <div className="flex items-center gap-4 flex-wrap">
              <PropertyTypeRadio value={typeFilter} onChange={setTypeFilter} />
              <PhotoFilterRadio value={photoFilter} onChange={setPhotoFilter} />
              <span className="text-xs text-pn-muted">{visible.length} listing{visible.length !== 1 ? 's' : ''}</span>
            </div>
          </div>
          <ZipCodeFilter selected={zipFilter} onChange={setZipFilter} zips={availableZips} />
        </div>

        {status === 'loading' && (
          <Empty message="Loading listings…" />
        )}

        {status === 'error' && (
          <Empty message="Could not load listings. Please try again later." />
        )}

        {status === 'ok' && visible.length === 0 && (
          <Empty
            message={
              listings.length === 0
                ? 'No listings yet — the first data refresh is pending.'
                : 'No listings match the current photo filter.'
            }
          />
        )}

        {status === 'ok' && visible.length > 0 && (
          <div
            className="grid gap-5"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(330px, 1fr))' }}
          >
            {visible.map(l => (
              <ListingCard key={l.zpid} listing={l} lastRunDate={lastRunDate} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Empty({ message }) {
  return (
    <div className="flex flex-col items-center justify-center py-28 gap-3 text-pn-muted">
      <span className="text-4xl">🏠</span>
      <p className="text-sm">{message}</p>
    </div>
  )
}
