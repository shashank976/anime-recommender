import React, { useState, useEffect, useRef, useCallback } from 'react';

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:5001';

const imageCache = {};

async function fetchAnimeImage(malId, title) {
  const key = malId || title;
  if (imageCache[key] !== undefined) return imageCache[key];
  try {
    const url_path = malId 
      ? `https://api.jikan.moe/v4/anime/${malId}` 
      : `https://api.jikan.moe/v4/anime?q=${encodeURIComponent(title)}&limit=1`;
    const res = await fetch(url_path);
    if (res.status === 429) {
      await new Promise(r => setTimeout(r, 2000));
      const retry = await fetch(url_path);
      const data = await retry.json();
      const url = malId 
        ? data.data?.images?.jpg?.large_image_url || ''
        : data.data?.[0]?.images?.jpg?.large_image_url || '';
      imageCache[key] = url;
      return url;
    }
    const data = await res.json();
    const url = malId 
      ? data.data?.images?.jpg?.large_image_url || ''
      : data.data?.[0]?.images?.jpg?.large_image_url || '';
    imageCache[key] = url;
    return url;
  } catch {
    imageCache[key] = '';
    return '';
  }
}


async function loadImagesSequentially(recs, onImageLoaded) {
  for (const rec of recs) {
    const key = rec.english_name || rec.name;
    const url = await fetchAnimeImage(rec.mal_id, key);
    onImageLoaded(key, url);
    await new Promise(r => setTimeout(r, 1000));
  }
}

const GENRE_COLORS = {
  Action: '#ff4757', Adventure: '#ff6b35', Comedy: '#ffd32a',
  Drama: '#a55eea', Fantasy: '#45aaf2', Horror: '#ff2d55',
  Mystery: '#778ca3', Romance: '#fd79a8', 'Sci-Fi': '#00d2d3',
  'Slice of Life': '#26de81', Sports: '#ff7f50', Supernatural: '#b46ef5',
  Thriller: '#596275', Default: '#636e72',
};

const CSS = `
  @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

  * { box-sizing: border-box; margin: 0; padding: 0; }

  body {
    background: #080808;
    color: #e8e8e8;
    font-family: 'DM Sans', sans-serif;
    min-height: 100vh;
  }

  .app-root {
    min-height: 100vh;
    background: #080808;
    position: relative;
    overflow-x: hidden;
  }

  .noise {
    position: fixed; inset: 0; z-index: 0; pointer-events: none;
    opacity: 0.035;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)'/%3E%3C/svg%3E");
    background-size: 200px 200px;
  }

  .accent-orb {
    position: fixed;
    width: 600px; height: 600px;
    border-radius: 50%;
    filter: blur(120px);
    pointer-events: none;
    z-index: 0;
    opacity: 0.07;
  }

  .orb-1 { background: #e63946; top: -200px; left: -200px; }
  .orb-2 { background: #457b9d; bottom: -200px; right: -200px; }

  .hero {
    position: relative; z-index: 1;
    padding: 72px 24px 48px;
    text-align: center;
  }

  .eyebrow {
    font-family: 'DM Sans', sans-serif;
    font-size: 11px;
    letter-spacing: 5px;
    text-transform: uppercase;
    color: #e63946;
    margin-bottom: 16px;
    display: flex; align-items: center; justify-content: center; gap: 10px;
  }

  .eyebrow::before, .eyebrow::after {
    content: '';
    width: 28px; height: 1px;
    background: #e63946;
    opacity: 0.6;
  }

  .hero-title {
    font-family: 'Syne', sans-serif;
    font-size: clamp(36px, 6vw, 72px);
    font-weight: 800;
    line-height: 1;
    letter-spacing: -2px;
    color: #f0f0f0;
    margin-bottom: 6px;
  }

  .hero-title span {
    color: #e63946;
  }

  .hero-sub {
    font-size: 14px;
    color: #555;
    margin-top: 14px;
    font-weight: 300;
    letter-spacing: 0.3px;
  }

  .search-zone {
    position: relative; z-index: 10;
    max-width: 640px;
    margin: 0 auto;
    padding: 0 24px;
  }

  .search-row {
    display: flex; gap: 8px; align-items: stretch;
  }

  .search-wrap {
    position: relative; flex: 1;
  }

  .search-input {
    width: 100%;
    padding: 14px 18px;
    background: #111;
    border: 1px solid #222;
    border-radius: 10px;
    color: #f0f0f0;
    font-size: 15px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color 0.2s;
  }

  .search-input::placeholder { color: #333; }

  .search-input:focus {
    border-color: #e63946;
  }

  .recommend-btn {
    padding: 14px 22px;
    background: #e63946;
    color: #fff;
    border: none;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    white-space: nowrap;
    letter-spacing: 0.3px;
    transition: background 0.15s, transform 0.1s;
  }

  .recommend-btn:hover { background: #c1121f; }
  .recommend-btn:active { transform: scale(0.97); }
  .recommend-btn:disabled { background: #222; color: #444; cursor: not-allowed; }

  .autocomplete-list {
    position: absolute; top: calc(100% + 6px); left: 0; right: 0;
    background: #111;
    border: 1px solid #222;
    border-radius: 10px;
    overflow: hidden;
    z-index: 100;
    box-shadow: 0 20px 60px rgba(0,0,0,0.6);
    max-height: 260px;
    overflow-y: auto;
  }

  .autocomplete-item {
    padding: 10px 16px;
    display: flex; justify-content: space-between; align-items: center;
    cursor: pointer;
    font-size: 13px;
    color: #bbb;
    transition: background 0.1s;
  }

  .autocomplete-item:hover { background: #181818; color: #f0f0f0; }

  .autocomplete-score {
    font-size: 11px;
    color: #e63946;
    font-weight: 600;
  }

  .filter-toggle {
    margin-top: 10px;
    background: none;
    border: 1px solid #1e1e1e;
    color: #444;
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 12px;
    font-family: 'DM Sans', sans-serif;
    cursor: pointer;
    display: flex; align-items: center; gap: 6px;
    letter-spacing: 0.3px;
    transition: border-color 0.15s, color 0.15s;
  }

  .filter-toggle:hover { border-color: #333; color: #777; }

  .filter-badge {
    background: #e63946;
    color: #fff;
    border-radius: 10px;
    padding: 1px 7px;
    font-size: 10px;
  }

  .filter-panel {
    margin-top: 8px;
    padding: 18px;
    background: #0e0e0e;
    border: 1px solid #1a1a1a;
    border-radius: 10px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }

  .filter-label {
    display: block;
    font-size: 10px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #333;
    margin-bottom: 6px;
  }

  .filter-select, .filter-input {
    width: 100%;
    padding: 8px 10px;
    background: #111;
    border: 1px solid #1e1e1e;
    border-radius: 6px;
    color: #aaa;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    outline: none;
    transition: border-color 0.15s;
  }

  .filter-select:focus, .filter-input:focus { border-color: #333; }
  .filter-select option { background: #111; }

  .clear-btn {
    background: none; border: none;
    color: #e63946; font-size: 12px;
    cursor: pointer; font-family: 'DM Sans', sans-serif;
    opacity: 0.7; transition: opacity 0.15s;
  }
  .clear-btn:hover { opacity: 1; }

  .results-zone {
    position: relative; z-index: 1;
    max-width: 640px;
    margin: 0 auto;
    padding: 28px 24px 80px;
  }

  .results-count {
    font-size: 11px;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: #333;
    margin-bottom: 20px;
  }

  .cards-list {
    display: flex; flex-direction: column; gap: 1px;
  }

  .anime-card {
    display: flex; gap: 0;
    background: #0d0d0d;
    border: 1px solid #161616;
    border-radius: 12px;
    overflow: hidden;
    transition: border-color 0.2s, transform 0.2s;
    margin-bottom: 10px;
  }

  .anime-card:hover {
    border-color: #2a2a2a;
    transform: translateX(3px);
  }

  .card-poster {
    flex-shrink: 0;
    width: 80px;
  }

  .card-poster img {
    width: 80px; height: 120px;
    object-fit: cover; display: block;
  }

  .card-poster-placeholder {
    width: 80px; height: 120px;
    background: #111;
    display: flex; align-items: center; justify-content: center;
  }

  .card-body {
    flex: 1; padding: 14px 16px; min-width: 0;
  }

  .card-top {
    display: flex; justify-content: space-between;
    align-items: flex-start; gap: 8px;
  }

  .card-title {
    font-family: 'Syne', sans-serif;
    font-size: 14px;
    font-weight: 700;
    color: #f0f0f0;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }

  .card-orig {
    font-size: 10px; color: #333; margin-top: 2px;
  }

  .score-badge {
    display: flex; align-items: center; gap: 3px;
    font-size: 13px; font-weight: 700;
    white-space: nowrap; flex-shrink: 0;
  }

  .card-meta {
    display: flex; gap: 10px; margin-top: 7px;
    font-size: 11px; color: #333; letter-spacing: 0.3px;
  }

  .genre-pills {
    display: flex; flex-wrap: wrap; gap: 4px; margin-top: 8px;
  }

  .genre-pill {
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.3px;
  }

  .reasons-box {
    margin-top: 8px;
    padding: 6px 10px;
    background: #111;
    border-left: 2px solid #e63946;
    border-radius: 0 4px 4px 0;
    font-size: 11px;
    color: #555;
    line-height: 1.7;
  }

  .synopsis-toggle {
    background: none; border: none; padding: 0;
    font-size: 10px; color: #333; cursor: pointer;
    font-family: 'DM Sans', sans-serif;
    margin-top: 8px; letter-spacing: 0.5px;
    text-transform: uppercase;
    transition: color 0.15s;
  }
  .synopsis-toggle:hover { color: #555; }

  .synopsis-text {
    margin-top: 6px; font-size: 12px; color: #444;
    line-height: 1.7; max-height: 90px; overflow-y: auto;
  }

  .error-box {
    padding: 12px 16px;
    background: #1a0a0a;
    border: 1px solid #3a1a1a;
    border-radius: 8px;
    color: #e63946;
    font-size: 13px;
    margin-bottom: 20px;
  }

  .spinner-wrap {
    text-align: center; padding: 60px 0; color: #333;
    font-size: 12px; letter-spacing: 2px; text-transform: uppercase;
  }

  .spinner {
    width: 28px; height: 28px;
    border: 2px solid #1a1a1a;
    border-top-color: #e63946;
    border-radius: 50%;
    animation: spin 0.7s linear infinite;
    margin: 0 auto 14px;
  }

  @keyframes spin { to { transform: rotate(360deg); } }

  .divider {
    width: 40px; height: 2px;
    background: #e63946;
    margin: 20px auto 32px;
    opacity: 0.4;
  }
`;

function GenrePill({ genre }) {
  const color = GENRE_COLORS[genre] || GENRE_COLORS.Default;
  return (
    <span className="genre-pill" style={{
      backgroundColor: color + '15',
      color: color,
      border: `1px solid ${color}25`,
    }}>
      {genre}
    </span>
  );
}

function ScoreBadge({ score }) {
  const color = score >= 8.5 ? '#26de81' : score >= 7.5 ? '#ffd32a' : '#e63946';
  return (
    <div className="score-badge" style={{ color }}>
      <svg width="11" height="11" viewBox="0 0 24 24" fill={color}>
        <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z" />
      </svg>
      {score?.toFixed(2) ?? 'N/A'}
    </div>
  );
}

function AnimeCard({ rec, imageUrl }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="anime-card">
      <div className="card-poster">
        {imageUrl
          ? <img src={imageUrl} alt={rec.english_name || rec.name} />
          : <div className="card-poster-placeholder">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#222" strokeWidth="1.5">
                <rect x="2" y="3" width="20" height="14" rx="2" />
                <path d="M8 21h8M12 17v4" />
              </svg>
            </div>
        }
      </div>
      <div className="card-body">
        <div className="card-top">
          <div style={{ minWidth: 0 }}>
            <div className="card-title">{rec.english_name || rec.name}</div>
            {rec.english_name && rec.english_name !== rec.name &&
              <div className="card-orig">{rec.name}</div>}
          </div>
          <ScoreBadge score={rec.score} />
        </div>

        <div className="card-meta">
          {rec.episodes && <span>{rec.episodes} eps</span>}
          {rec.type && <span style={{ textTransform: 'uppercase', letterSpacing: 1 }}>{rec.type}</span>}
        </div>

        <div className="genre-pills">
          {(rec.genres || []).slice(0, 4).map(g => <GenrePill key={g} genre={g} />)}
        </div>

        {rec.reasons?.length > 0 && (
          <div className="reasons-box">
            {rec.reasons.map((r, i) => <div key={i}>{i === 0 ? '↳ ' : '  '}{r}</div>)}
          </div>
        )}

        {rec.synopsis && (
          <>
            <button className="synopsis-toggle" onClick={() => setExpanded(e => !e)}>
              {expanded ? '▴ hide' : '▾ synopsis'}
            </button>
            {expanded && <p className="synopsis-text">{rec.synopsis}</p>}
          </>
        )}
      </div>
    </div>
  );
}

function Autocomplete({ value, onChange, onSelect, onSubmit, suggestions }) {
  const [open, setOpen] = useState(false);
  const ref = useRef();

  useEffect(() => {
    const h = (e) => { if (!ref.current?.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  useEffect(() => { setOpen(suggestions.length > 0); }, [suggestions]);

  return (
    <div ref={ref} className="search-wrap">
      <input
        className="search-input"
        value={value}
        onChange={e => onChange(e.target.value)}
        onFocus={() => suggestions.length > 0 && setOpen(true)}
        onKeyDown={e => {
          if (e.key === 'Enter') { setOpen(false); onSubmit(); }
          if (e.key === 'Escape') setOpen(false);
        }}
        placeholder="Attack on Titan, Naruto, Vinland Saga..."
      />
      {open && (
        <div className="autocomplete-list">
          {suggestions.map((s, i) => (
            <div
              key={i}
              className="autocomplete-item"
              onMouseDown={() => { onSelect(s); setOpen(false); }}
            >
              <span>{s.english_name || s.name}</span>
              {s.score && <span className="autocomplete-score">★ {s.score.toFixed(1)}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [query, setQuery] = useState('');
  const [selectedTitle, setSelectedTitle] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [recommendations, setRecommendations] = useState([]);
  const [images, setImages] = useState({});
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [genres, setGenres] = useState([]);
  const [filters, setFilters] = useState({ genre: '', min_score: '', min_episodes: '', max_episodes: '' });
  const [showFilters, setShowFilters] = useState(false);
  const debounceRef = useRef();

  useEffect(() => {
    fetch(`${API_BASE}/genres`)
      .then(r => r.json())
      .then(d => setGenres(d.genres || []))
      .catch(() => {});
  }, []);

  useEffect(() => {
    clearTimeout(debounceRef.current);
    if (query.length < 2) { setSuggestions([]); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const res = await fetch(`${API_BASE}/search?q=${encodeURIComponent(query)}`);
        const data = await res.json();
        setSuggestions(data.results || []);
      } catch { setSuggestions([]); }
    }, 250);
  }, [query]);

  const getRecommendations = useCallback(async () => {
    const title = selectedTitle || query;
    if (!title.trim()) return;
    setLoading(true);
    setError('');
    setRecommendations([]);
    setImages({});
    try {
      const params = new URLSearchParams({ title });
      if (filters.genre) params.append('genre', filters.genre);
      if (filters.min_score) params.append('min_score', filters.min_score);
      if (filters.min_episodes) params.append('min_episodes', filters.min_episodes);
      if (filters.max_episodes) params.append('max_episodes', filters.max_episodes);
      const res = await fetch(`${API_BASE}/recommend?${params}`);
      const data = await res.json();
      if (data.error) {
        setError(data.error);
      } else {
        setRecommendations(data.recommendations || []);
        loadImagesSequentially(
        data.recommendations,  // pass full rec objects now, not just titles
        (title, url) => setImages(prev => ({ ...prev, [title]: url }))
        );
      }
    } catch {
      setError('Could not connect to server. Is Flask running on port 5001?');
    } finally {
      setLoading(false);
    }
  }, [query, selectedTitle, filters]);

  const handleSelect = (s) => {
    const name = s.english_name || s.name;
    setQuery(name);
    setSelectedTitle(s.name);
    setSuggestions([]);
  };

  const activeFilters = Object.values(filters).filter(v => v).length;

  return (
    <>
      <style>{CSS}</style>
      <div className="app-root">
        <div className="noise" />
        <div className="accent-orb orb-1" />
        <div className="accent-orb orb-2" />

        <div className="hero">
          <h1 className="hero-title">Anime<span>.</span>Find</h1>
          <div className="divider" />
          <p className="hero-sub">Discover series you'll actually finish</p>
        </div>

        <div className="search-zone">
          <div className="search-row">
            <Autocomplete
              value={query}
              onChange={(v) => { setQuery(v); setSelectedTitle(''); }}
              onSelect={handleSelect}
              onSubmit={getRecommendations}
              suggestions={suggestions}
            />
            <button
              className="recommend-btn"
              onClick={getRecommendations}
              disabled={loading}
            >
              {loading ? 'Searching...' : 'Find →'}
            </button>
          </div>

          <button className="filter-toggle" onClick={() => setShowFilters(f => !f)}>
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="4" y1="6" x2="20" y2="6" />
              <line x1="8" y1="12" x2="16" y2="12" />
              <line x1="11" y1="18" x2="13" y2="18" />
            </svg>
            Filters
            {activeFilters > 0 && <span className="filter-badge">{activeFilters}</span>}
          </button>

          {showFilters && (
            <div className="filter-panel">
              <div>
                <label className="filter-label">Genre</label>
                <select className="filter-select" value={filters.genre}
                  onChange={e => setFilters(f => ({ ...f, genre: e.target.value }))}>
                  <option value="">Any</option>
                  {genres.map(g => <option key={g} value={g}>{g}</option>)}
                </select>
              </div>
              <div>
                <label className="filter-label">Min Score</label>
                <select className="filter-select" value={filters.min_score}
                  onChange={e => setFilters(f => ({ ...f, min_score: e.target.value }))}>
                  <option value="">Any</option>
                  {[7.0, 7.5, 8.0, 8.5, 9.0].map(s => (
                    <option key={s} value={s}>≥ {s.toFixed(1)}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="filter-label">Min Episodes</label>
                <input className="filter-input" type="number" min="1" placeholder="e.g. 12"
                  value={filters.min_episodes}
                  onChange={e => setFilters(f => ({ ...f, min_episodes: e.target.value }))} />
              </div>
              <div>
                <label className="filter-label">Max Episodes</label>
                <input className="filter-input" type="number" min="1" placeholder="e.g. 24"
                  value={filters.max_episodes}
                  onChange={e => setFilters(f => ({ ...f, max_episodes: e.target.value }))} />
              </div>
              <div style={{ gridColumn: '1 / -1', textAlign: 'right' }}>
                <button className="clear-btn"
                  onClick={() => setFilters({ genre: '', min_score: '', min_episodes: '', max_episodes: '' })}>
                  Clear all
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="results-zone">
          {error && <div className="error-box">{error}</div>}

          {loading && (
            <div className="spinner-wrap">
              <div className="spinner" />
              Finding recommendations
            </div>
          )}

          {!loading && recommendations.length > 0 && (
            <>
              <div className="results-count">
                {recommendations.length} results
                {activeFilters > 0 ? ` · ${activeFilters} filter${activeFilters > 1 ? 's' : ''} active` : ''}
              </div>
              <div className="cards-list">
                {recommendations.map((rec, i) => {
                  const key = rec.english_name || rec.name;
                  return <AnimeCard key={i} rec={rec} imageUrl={images[key]} />;
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}