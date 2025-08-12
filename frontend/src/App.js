import React, { useState } from 'react';
import './App.css';

function App() {
  const [title, setTitle] = useState('');
  const [recommendations, setRecommendations] = useState([]);
  const [error, setError] = useState('');

  // Helper function to fetch anime image from Jikan
  const fetchAnimeImage = async (animeTitle) => {
    try {
      const res = await fetch(`https://api.jikan.moe/v4/anime?q=${encodeURIComponent(animeTitle)}&limit=1`);
      const data = await res.json();
      return data.data?.[0]?.images?.jpg?.image_url || '';
    } catch (err) {
      console.error("Error fetching image:", err);
      return '';
    }
  };

  const API_BASE = process.env.REACT_APP_API_URL || 'https://anime-recommender-738z.onrender.com';

  // Main function to get recommendations from Flask and attach images
  const getRecommendations = async () => {
    try {
      const response = await fetch(`${API_BASE}/recommend?title=${encodeURIComponent(title)}`);
      const data = await response.json();

      if (data.error) {
        setError(data.error);
        setRecommendations([]);
      } else {
        const withImages = await Promise.all(
          data.recommendations.map(async (rec) => {
            const name = rec.split(' (score: ')[0];  // Extract anime title
            const scoreMatch = rec.match(/\d+(\.\d+)?/); // Extract score
            const score = scoreMatch ? scoreMatch[0] : 'N/A';
            const image_url = await fetchAnimeImage(name);

            return { name, score, image_url };
          })
        );

        setRecommendations(withImages);
        setError('');
      }
    } catch (err) {
      setError('Server error. Is Flask running on port 5001?');
      setRecommendations([]);
    }
  };

  return (
    <div style={{ padding: 40, fontFamily: 'Arial' }}>
      <h1>Anime Recommender</h1>

      {/* Input and Button */}
      <input
        type="text"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        placeholder="Enter anime title..."
        style={{ padding: 10, fontSize: 16, width: 300 }}
      />
      <button onClick={getRecommendations} style={{ marginLeft: 10, padding: 10 }}>
        Recommend
      </button>

      {/* Error Display */}
      {error && <p style={{ color: 'red' }}>{error}</p>}

      {/* Recommendations List */}
      <ul style={{ listStyle: 'none', padding: 0 }}>
        {recommendations.map((rec, i) => (
          <li key={i} style={{ display: 'flex', alignItems: 'center', marginBottom: 16 }}>
            {rec.image_url ? (
              <img
                src={rec.image_url}
                alt={rec.name}
                style={{ width: 80, height: 100, marginRight: 16, borderRadius: 8 }}
              />
            ) : (
              <div style={{ width: 80, height: 100, marginRight: 16, backgroundColor: '#ccc' }} />
            )}
            <div>
              <strong>{rec.name}</strong><br />
              Score: {rec.score}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default App;
