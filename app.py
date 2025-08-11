from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import joblib



app = Flask(__name__)
CORS(app, supports_credentials=True)
# Load preprocessed data
df_anime = joblib.load('df_anime.pkl')
cosine_sim = joblib.load('cosine_sim.pkl')

def get_recommendations(input_titles, cosine_sim, df, top_n=20, score_weight=0.04):
    
    #Recommends anime based on input titles, considering cosine similarity and anime scores.
    # Find indices of input titles in the dataset
    input_indices = []
    for title in input_titles:
        matches = df[(df['Name'].str.lower() == title.lower()) | (df['English name'].str.lower() == title.lower())]
        if not matches.empty:
            input_indices.append(matches.iloc[0].name)
        else:
            print(f"Anime '{title}' not found in the dataset.")
    
    if not input_indices:
        return []

    type_penalty = np.array([0.0 if t in ['TV', 'Movie', 'ONA'] else -0.2 for t in df['Type'].str.lower()])
    # Compute the average similarity scores for all anime
    sim_scores = np.mean(cosine_sim[input_indices], axis=0)
    
    # Adjust similarity scores using the score column
    adjusted_scores = sim_scores + (score_weight * df['Score'].values) + type_penalty

    # Sort by adjusted scores and get the top indices
    top_indices = adjusted_scores.argsort()[-(50 + len(input_indices)):][::-1]
    # Exclude the input anime themselves
    top_indices = [i for i in top_indices if i not in input_indices]

    # Get the full recommendations
    recommendations = df.iloc[top_indices][['Name', 'Score']].values

    recommendations = deduplicate_franchise(recommendations, input_titles[0])

    # Return only top N after deduplication
    recommendations = recommendations[:top_n]       
    return recommendations

def deduplicate_franchise(recs, base_title):
    base = base_title.lower().split()[0]
    seen_franchises = set()
    final_recs = []

    for name, score in recs:
        name_lower = name.lower()

        # Only keep one anime per franchise name
        if base in name_lower:
            if base in seen_franchises:
                continue
            seen_franchises.add(base)

        final_recs.append([name, score])

    return final_recs



@app.route('/recommend', methods=['GET'])
def recommend():
    title = request.args.get('title')  # ?title=Naruto
    if not title:
        return jsonify({'error': 'No title provided'}), 400

    recs = get_recommendations([title], cosine_sim, df_anime, top_n=20, score_weight=0.05)
    return jsonify({'recommendations': [f"{name} (score: {score})" for name, score in recs]})

if __name__ == '__main__':
    app.run(debug=True, port=5001)
