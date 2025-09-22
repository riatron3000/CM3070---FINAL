# music/utils.py
from rapidfuzz import process
import pandas as pd
from collections import Counter
from gensim.models import FastText
import re
from datetime import datetime
from django.utils.timezone import now
import numpy as np
import os


# BASE_DIR helloworld/
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIMPLESITE_DIR = os.path.dirname(BASE_DIR)       # simplesite/
PROJECT_DIR = os.path.dirname(SIMPLESITE_DIR)   # project/

DATA_DIR = os.path.join(PROJECT_DIR, "data")    # nexttrack/project/data/

# load csv, embeddings, model
df = pd.read_csv(os.path.join(DATA_DIR, "final_df.csv"))
track_matrix = np.load(os.path.join(DATA_DIR, "track_matrix_final2.npy"))
fasttext_model2 = FastText.load(os.path.join(DATA_DIR, "fasttext_tag_model2_final.model"))
wv = fasttext_model2
print("models and data loaded")