# prepare_data.py
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib

df_anime = pd.read_csv('anime-filtered.csv', usecols=['anime_id','Name', 'English name', 'Genres', 'Score', 'Episodes', 'sypnopsis', 'Type', 'Popularity'])
print("Rows remaining:", len(df_anime))
valid_types = ['TV', 'Movie', 'ONA']
df_anime = df_anime[df_anime['Type'].isin(valid_types)].drop_duplicates(subset='Name')
#drop specials
def valid_episode_count(row):
    ep = str(row['Episodes'])
    if not ep.isdigit():
        return False
    ep = int(ep)
    if row['Type'] in ['TV', 'ONA']:
        return ep >= 6
    return True


bad_synopsis_patterns = [
    "unknown",
    "no synopsis information",
    "help improve our database",
    "recap of episodes",
    "compilation of episodes",
    "second season",
    "R2"
]

mask_syn = ~df_anime['sypnopsis'].str.lower().str.contains(
    '|'.join(bad_synopsis_patterns),
    na=False
)

df_anime = df_anime[mask_syn]
print("Rows remaining:", len(df_anime))


#making sure needed features are valid
df_anime['English name'] = df_anime['English name'].fillna(df_anime['Name'])
df_anime.loc[
    df_anime['English name'].str.lower() == 'unknown',
    'English name'
] = df_anime['Name']
df_anime = df_anime[df_anime.apply(valid_episode_count, axis=1)]
df_anime['Episodes'] = df_anime['Episodes'].astype(int)
df_anime = df_anime[df_anime['Score'].apply(lambda x: str(x).replace('.', '', 1).isdigit() and float(x) > 6.0)]
df_anime['Score'] = df_anime['Score'].astype(float)
df_anime = df_anime.dropna(subset=['Genres'])
df_anime['English name'] = df_anime['English name'].fillna(df_anime['Name'])
df_anime['sypnopsis'] = df_anime['sypnopsis'].fillna('')
df_anime['genre_str'] = df_anime['Genres'].apply(lambda x: ' '.join(x.split(', ')))
df_anime['combined_features'] = ((df_anime['genre_str'] + ' ')*3 +(df_anime['sypnopsis'] + ' ') * 2)
df_anime = df_anime.reset_index(drop=True)

# Normalize scores to [0,1] for blending later
scaler = MinMaxScaler()
score_scaled = scaler.fit_transform(df_anime[['Score']]).flatten()

popularity_scaler = MinMaxScaler()
# lower popularity rank = more popular
popularity_scaled = 1 - popularity_scaler.fit_transform(
    df_anime[['Popularity']]
).flatten()

# KNN model on features
tfidf = TfidfVectorizer(stop_words='english',max_df=0.8,ngram_range=(1,2),min_df=2)
tfidf_matrix = tfidf.fit_transform(df_anime['combined_features'])
knn=NearestNeighbors(metric='cosine', algorithm='brute')
knn.fit(tfidf_matrix)
# Save preprocessed objects
joblib.dump(popularity_scaled,"popularity_scaled.pkl")
joblib.dump(df_anime, "anime_df.pkl")
joblib.dump(tfidf, "tfidf.pkl")
joblib.dump(tfidf_matrix, "tfidf_matrix.pkl", compress=3)  # compress saves space
joblib.dump(knn, "knn.pkl")
joblib.dump(score_scaled, "score_scaled.pkl")
print("Rows remaining:", len(df_anime))
print('data preprocessed and saved')