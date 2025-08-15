import os
import gdown
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib

# Google Drive file IDs
model_files = {
    "anime_df.pkl": "https://drive.google.com/file/d/1iCcJeQpk8TcxCjJsxL8Ep45C5m4Plsxw/view?usp=sharing",
    "tfidf.pkl": "https://drive.google.com/file/d/1_4XQGLZDCzWalBpGqyQQ2FyB3tcII7gI/view?usp=sharing",
    "tfidf_matrix.pkl": "https://drive.google.com/file/d/1BQ8OwKs7U5OSP9nq3miwo8cPTyxpvAN9/view?usp=sharing",
    "knn.pkl": "https://drive.google.com/file/d/1z6Bo8MOv01mO5nHUEEDuOkVzY_9xMn8V/view?usp=sharing"
}

# Download missing files
for filename, file_id in model_files.items():
    if not os.path.exists(filename):
        url = f"https://drive.google.com/uc?id={file_id}"
        print(f"Downloading {filename}...")
        gdown.download(url, filename, quiet=False)
    else:
        print(f"{filename} already exists, skipping.")


app = Flask(__name__)
CORS(app, supports_credentials=True)
# Load preprocessed data
df_anime = joblib.load("models/anime_df.pkl")
tfidf = joblib.load("models/tfidf.pkl")
tfidf_matrix = joblib.load("models/tfidf_matrix.pkl")
knn = joblib.load("models/knn.pkl")


def get_recommendations_knn(title, knn_model, feature_matrix, df, top_n=50):
    # Find index for the input title
    matches = df[(df['Name'].str.lower() == title.lower()) |
                 (df['English name'].str.lower() == title.lower())]
    if matches.empty:
        return []

    idx = matches.index[0]
    # Ensure 2D input for KNN
    distances, indices = knn_model.kneighbors(feature_matrix[idx].reshape(1, -1), n_neighbors=top_n + 1)

    recommendations = []
    for i in range(1, len(indices[0])):  # Skip the first (it's the same anime)
        rec_idx = indices[0][i]
        name = df.iloc[rec_idx]['Name']
        score = df.iloc[rec_idx]['Score']
        if pd.notna(score):
            recommendations.append((name, score))

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
def recommend():
    title = request.args.get('title')  # ?title=Naruto
    if not title:
        return jsonify({'error': 'No title provided'}), 400

    recs = get_recommendations_knn(title, knn, tfidf_matrix, df_anime, top_n=50)
    recs = remove_duplicate_movies(recs)
    recs = deduplicate_franchise(recs, title)
    recs = recs[:20]  # Return top 20


    return jsonify({'recommendations': [f"{name} (score: {score})" for name, score in recs]})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
