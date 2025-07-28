import numpy as np
import pandas as pd
# Visualization
import plotly.express as px
import plotly.graph_objects as go  # for 3D plot visualization
import plotly.figure_factory as ff
from wordcloud import WordCloud
from langdetect import detect
from datetime import datetime
### Basic libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import pickle
import warnings
warnings.filterwarnings(action='ignore')

# Data Preprocessing
from sklearn.preprocessing import MinMaxScaler
from sklearn.preprocessing import LabelEncoder

# Model Training
from sklearn.utils import shuffle
from sklearn.model_selection import train_test_split
import tensorflow as tf

## Import necessary modules for content-based filtering
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel



pd.set_option('display.max_columns', 50)
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


# Example user input
user_input = ["a silent voice"]

# Get recommendations
recommendations = get_recommendations(user_input, cosine_sim, df_anime, top_n=20,score_weight=0.05)

# Print results

print("Recommended Anime:")
for i, rec in enumerate(recommendations, 1):
    print(f"{i}. {rec}")
