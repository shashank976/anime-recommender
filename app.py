import os
import gdown
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib
import pandas as pd


# Google Drive file IDs
model_files = {
    "anime_df.pkl": "https://drive.google.com/file/d/1xgjwFl8Nde4ETcNvf5ci109gQ4AAnys5/view?usp=sharing",
    "tfidf.pkl": "https://drive.google.com/file/d/1-7kHNvbRTci_KUuVxKwvD4RwndABu6pK/view?usp=sharing",
    "tfidf_matrix.pkl": "https://drive.google.com/file/d/1QXnxYijM2lyRYgmH5ALxL0gF4ksa6j6C/view?usp=sharing",
    "knn.pkl": "https://drive.google.com/file/d/1qiBJW6mDarbA4u8Ql8G9HxfmeRX22HFs/view?usp=sharing",
    "score_scaled.pkl": "https://drive.google.com/file/d/14fY7fHPVOOrQILlVWfo57GE4Jf5KJqUl/view?usp=sharing",
    "popularity_scaled.pkl":"https://drive.google.com/file/d/1-BYTM4tMwCW7gqE8vaGNx60DQ-eunS6P/view?usp=sharing"
}

os.makedirs("models", exist_ok=True)

# Download missing files
for filename, url in model_files.items():
    if not os.path.exists(filename):
        print(f"Downloading {filename}...")
        gdown.download(url, filename, quiet=False, fuzzy=True)
    else:
        print(f"{filename} already exists, skipping.")


app = Flask(__name__)
CORS(app, supports_credentials=True)

# Load preprocessed data
df_anime = joblib.load("anime_df.pkl")
df_anime = df_anime.reset_index(drop=True)
tfidf = joblib.load("tfidf.pkl")
tfidf_matrix = joblib.load("tfidf_matrix.pkl")
knn = joblib.load("knn.pkl")
scores_scaled=joblib.load("score_scaled.pkl")
popularity = joblib.load("popularity_scaled.pkl")
print("Loaded anime count:", len(df_anime))

print(len(df_anime))

def row_to_dict(row, cosine_sim=None, input_genres=None):
    """Convert a DataFrame row to a structured dict"""
    genres = [g.strip() for g in str(row.get('Genres', '')).split(',') if g.strip()]
 
    result = {
        "mal_id": int(row['anime_id']) if pd.notna(row.get('anime_id')) else None,
        "name": row.get('Name', ''),
        "english_name": row.get('English name', row.get('Name', '')),
        "score": float(row['Score']) if pd.notna(row.get('Score')) else None,
        "episodes": int(row['Episodes']) if pd.notna(row.get('Episodes')) else None,
        "genres": genres,
        "type": row.get('Type', ''),
        "synopsis": row.get('sypnopsis', '') or '',
    }
 
    # Build explanation tags
    if cosine_sim is not None and input_genres is not None:
        shared = [g for g in genres if g in input_genres]
        reasons = []
        if shared:
            reasons.append(f"Similar genres: {', '.join(shared[:3])}")
        if cosine_sim > 0.5:
            reasons.append("Very similar themes and story")
        elif cosine_sim > 0.3:
            reasons.append("Similar themes")
        result["reasons"] = reasons
        result["similarity"] = round(cosine_sim, 3)
 
    return result
 

def get_recommendations_knn(title, knn_model, feature_matrix, df, scores, popularity, top_n=50):
    # Find index for the input title
    matches = df[
        (df['Name'].str.lower() == title.lower()) |
        (df['English name'].str.lower() == title.lower())
    ]

    if matches.empty:
        return []

    idx = matches.index[0]
    # Ensure 2D input for KNN
    distances, indices = knn_model.kneighbors(feature_matrix[idx], n_neighbors=top_n + 1)

    recommendations = []
    for i in range(1, len(indices[0])):  # skip first (same anime)
        rec_idx = indices[0][i]
        cosine_sim = 1 - distances[0][i]  # convert distance -> similarity
        hybrid =  0.65 * cosine_sim + 0.20 * scores[rec_idx] +0.15 * popularity[rec_idx]

        recommendations.append((rec_idx, cosine_sim, hybrid))
    
    return recommendations

def remove_duplicate_movies(recommendations, df):
    final = []
    seen_franchise = set()
    for rec_idx, cosine_sim, hybrid in recommendations:
        name = df.iloc[rec_idx]['Name']
        lower = name.lower()
        base = lower.split(':')[0].split()[0]
        if "movie" in lower:
            if base in seen_franchise:
                continue
            seen_franchise.add(base)
        final.append((rec_idx, cosine_sim, hybrid))
    return final
 


def deduplicate_franchise(recommendations, input_title, df):
    import re
    def base(s):
        s = re.sub(r'[^a-z0-9 ]', '', s.lower())  # strip punctuation
        return s.split(':')[0].split()[0]
    
    input_base = base(input_title)
    return [
        (rec_idx, cosine_sim, hybrid)
        for rec_idx, cosine_sim, hybrid in recommendations
        if input_base not in re.sub(r'[^a-z0-9 ]', '', df.iloc[rec_idx]['Name'].lower())
    ]


@app.route('/recommend', methods=['GET'])
def recommend():

    bad_words = [
        "season 1",
        "season 2",
        "season 3",
        "season 4",
        "season 5",
        "1st season",
        "2nd season",
        "3rd season",
        "4th season",
        "5th season",
        "first season",
        "second season",
        "third season",
        "fourth season",
        "fifth season",
        "final season",
        "part 2",
        "part 3",
        "part 4",
        "part 5",
        "movie",
        "act",
        "cour",
        "R2"
    ]

    title = request.args.get('title', '').strip()  # ?title=Naruto
    if not title:
        return jsonify({'error': 'No title provided'}), 400

    recs = get_recommendations_knn(title, knn, tfidf_matrix, df_anime, scores_scaled, popularity,top_n=80)

    matches = df_anime[
        (df_anime['Name'].str.lower() == title.lower()) |
        (df_anime['English name'].str.lower() == title.lower())
    ]

    input_genres = []
    if not matches.empty:
        input_genres = [
            g.strip()
            for g in str(matches.iloc[0]['Genres']).split(',')
            if g.strip()
        ]

    #optional filters
    genre_filter = request.args.get('genre', '').strip().lower()
    min_score = request.args.get('min_score', type=float)
    max_episodes = request.args.get('max_episodes', type=int)
    min_episodes = request.args.get('min_episodes', type=int)

    if not recs:
        return jsonify({'error': f'No recommendations found for "{title}"'}), 404

    # Sort by hybrid score descending
    recs.sort(key=lambda x: x[2], reverse=True)

    # Deduplicate movies/franchise
    recs = remove_duplicate_movies(recs, df_anime)
    recs = deduplicate_franchise(recs, title, df_anime)

    results = []
    for rec_idx, cosine_sim, hybrid in recs:
        row = df_anime.iloc[rec_idx]
        name = str(row["Name"]).lower()
        if any(word in name for word in bad_words):
            continue
        row = df_anime.iloc[rec_idx]
        if row['Type'] == 'Movie' and any(w in name for w in ['chronicle', 'recap', 'compilation', 'memorial']):
            continue
        if genre_filter:
            genres_lower = str(row.get('Genres', '')).lower()
            if genre_filter not in genres_lower:
                continue
        if min_score is not None:
            try:
                if float(row['Score']) < min_score:
                    continue
            except (ValueError, TypeError):
                continue
        if min_episodes is not None:
            try:
                if int(row['Episodes']) < min_episodes:
                    continue
            except (ValueError, TypeError):
                continue
        if max_episodes is not None:
            try:
                if int(row['Episodes']) > max_episodes:
                    continue
            except (ValueError, TypeError):
                continue
    
        results.append(row_to_dict(row, cosine_sim=cosine_sim, input_genres=input_genres))
        if len(results) >= 20:
            break
    

    return jsonify({'input_title': title,  'recommendations': results})


@app.route('/search', methods=['GET'])
def search():
    """Autocomplete endpoint: returns up to 10 matching titles."""
    query = request.args.get('q', '').strip().lower()
    if not query or len(query) < 2:
        return jsonify({'results': []})
 
    mask = (
        df_anime['Name'].str.lower().str.contains(query, na=False) |
        df_anime['English name'].str.lower().str.contains(query, na=False)
    )
    matches = df_anime[mask].head(10)
 
    results = []
    for _, row in matches.iterrows():
        results.append({
            'name': row['Name'],
            'english_name': row.get('English name', row['Name']),
            'score': float(row['Score']) if pd.notna(row.get('Score')) else None,
        })
 
    return jsonify({'results': results})
 
 
@app.route('/genres', methods=['GET'])
def genres():
    """Return all unique genres for filter dropdown."""
    all_genres = set()
    for genre_str in df_anime['Genres'].dropna():
        for g in genre_str.split(','):
            g = g.strip()
            if g:
                all_genres.add(g)
    return jsonify({'genres': sorted(all_genres)})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
