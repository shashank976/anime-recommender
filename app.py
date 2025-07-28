from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_cors import cross_origin
import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

app = Flask(__name__)
CORS(app, supports_credentials=True)
df_anime=pd.read_csv('anime-filtered.csv', usecols=['Name','English name','Genres','Score','Episodes','sypnopsis','Type'])

#scale scores 0-1
scaler = MinMaxScaler()
df_anime['score'] = scaler.fit_transform(df_anime[['Score']])
valid_types = ['TV', 'Movie', 'ONA']
df_anime = df_anime[df_anime['Type'].isin(valid_types)]
df_anime = df_anime.drop_duplicates(subset='Name')


def valid_episode_count(row):
    ep = str(row['Episodes'])
    if not ep.isdigit():
        return False
    ep = int(ep)
    if row['Type'] in ['TV', 'ONA']:
        return ep >= 6
    return True


df_anime = df_anime[df_anime.apply(valid_episode_count, axis=1)]
df_anime['Episodes'] = df_anime['Episodes'].astype(int)

df_anime = df_anime[df_anime['Score'].apply(lambda x: str(x).replace('.', '', 1).isdigit() and float(x) > 6.0)]
df_anime['Score'] = df_anime['Score'].astype(float)

df_anime = df_anime.dropna(subset=['Genres'])
df_anime['English name'] = df_anime['English name'].fillna(df_anime['Name'])
df_anime['sypnopsis'] = df_anime['sypnopsis'].fillna('')
#converted genre strings into clean word lists
df_anime['genre_str'] = df_anime['Genres'].apply(lambda x: ' '.join(x.split(', ')))

df_anime['combined_features'] = df_anime['genre_str'] + ' ' + df_anime['sypnopsis']

print(df_anime.head())  # Check the first few rows
print(df_anime.info())  # Get dataset structure and non-null counts

df_anime = df_anime.reset_index(drop=True)

tfidf=TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(df_anime['combined_features'])

cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)
print(f"Cosine similarity matrix shape: {cosine_sim.shape}")



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

    # Deduplicate by franchise
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
