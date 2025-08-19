import os
import gdown
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib
import pandas as pd


# Google Drive file IDs
model_files = {
    "anime_df.pkl": "https://drive.google.com/file/d/1lFvWIbB9kJlj0KjBZsexHi83BQkdjcAZ/view?usp=sharing",
    "tfidf.pkl": "https://drive.google.com/file/d/1wRNFYwOPE0Z1YjqkEK2JK7tBHBDTd-cW/view?usp=sharing",
    "tfidf_matrix.pkl": "https://drive.google.com/file/d/1nGG8wnMREVxuqox-VFK_G0hvqESl7R0f/view?usp=sharing",
    "knn.pkl": "https://drive.google.com/file/d/1fSizLyMlkoCwKMEs2r6NYKXrK7bGoXPQ/view?usp=sharing",
    "score_scaled.pkl": "https://drive.google.com/file/d/16XKBAjUUPA1M8PGsa6CHiz93BdaF7_eh/view?usp=sharing"
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


def get_recommendations_knn(title, knn_model, feature_matrix, df,scores, top_n=50,):
    # Find index for the input title
    matches = df[(df['Name'].str.lower() == title.lower()) |
                 (df['English name'].str.lower() == title.lower())]
    if matches.empty:
        return []

    idx = matches.index[0]
    # Ensure 2D input for KNN
    distances, indices = knn_model.kneighbors(feature_matrix[idx], n_neighbors=top_n + 1)

    recommendations = []
    for i in range(1, len(indices[0])):  # skip first (same anime)
        rec_idx = indices[0][i]
        name = df.iloc[rec_idx]['Name']
        mal_score = df.iloc[rec_idx]['Score']
        cosine_sim = 1 - distances[0][i]  # convert distance -> similarity
        hybrid = .7 * cosine_sim + (1 - .7) * scores[rec_idx]
        recommendations.append((name, mal_score, hybrid))
    
    return recommendations

def remove_duplicate_movies(recommendations):
    final_recs = []
    movie_seen_for_franchise = set()

    for name, score in recommendations:
        lower_name = name.lower()
        # Detect franchise (first word or before colon)
        base_franchise = lower_name.split(':')[0].split()[0]

        if "movie" in lower_name:
            if base_franchise in movie_seen_for_franchise:
                continue
            movie_seen_for_franchise.add(base_franchise)

        final_recs.append((name, score))

    return final_recs

def deduplicate_franchise(recommendations, input_title):
    """Remove anime from the same franchise as input"""
    input_base = input_title.lower().split(':')[0].split()[0]
    return [(name, score) for name, score in recommendations if input_base not in name.lower()]


@app.route('/recommend', methods=['GET'])
@app.route('/recommend', methods=['GET'])
def recommend():
    title = request.args.get('title')  # ?title=Naruto
    if not title:
        return jsonify({'error': 'No title provided'}), 400

    recs = get_recommendations_knn(title, knn, tfidf_matrix, df_anime, scores_scaled, top_n=50)

    if not recs:
        return jsonify({'error': f'No recommendations found for "{title}"'}), 404

    # Sort by hybrid score descending
    recs.sort(key=lambda x: x[2], reverse=True)

    # Deduplicate movies/franchise
    recs = remove_duplicate_movies(recs)
    recs = deduplicate_franchise(recs, title)

    # Return top 20
    recs = recs[:20]

    return jsonify({'recommendations': [f"{name} (score: {score:.2f})" for name, score in recs]})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
