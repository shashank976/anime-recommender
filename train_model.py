# prepare_data.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
import joblib

df_anime = pd.read_csv('anime-filtered.csv', usecols=['Name', 'English name', 'Genres', 'Score', 'Episodes', 'sypnopsis', 'Type'])

scaler = MinMaxScaler()
df_anime['score'] = scaler.fit_transform(df_anime[['Score']])
valid_types = ['TV', 'Movie', 'ONA']
df_anime = df_anime[df_anime['Type'].isin(valid_types)].drop_duplicates(subset='Name')

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
df_anime['genre_str'] = df_anime['Genres'].apply(lambda x: ' '.join(x.split(', ')))
df_anime['combined_features'] = df_anime['genre_str'] + ' ' + df_anime['sypnopsis']
df_anime = df_anime.reset_index(drop=True)

tfidf = TfidfVectorizer(stop_words='english')
tfidf_matrix = tfidf.fit_transform(df_anime['combined_features'])
cosine_sim = linear_kernel(tfidf_matrix, tfidf_matrix)

# Save preprocessed objects
joblib.dump(df_anime, 'df_anime.pkl')
joblib.dump(cosine_sim, 'cosine_sim.pkl')

print(" Data preprocessed and saved!")
