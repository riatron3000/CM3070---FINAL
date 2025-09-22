from collections import Counter
import pandas as pd
from .utils import *


# tags preprocessor: converts comma separated strings to lists
def preprocess_tags(tag_string):
    if pd.isna(tag_string):
        return []
    return [tag.strip().lower() for tag in tag_string.split(',')]


REMOVE_TAGS = {
    "artist_name", "spotify", "tags", "similar", "america", "usa", "seen live",
    "uk", "myspotigrambot", "taylor", "taylor swift", "overrated", "gay",
    "amazing", "queer", "genius", "brilliant", "love at first listen",
    "masterpiece", "personal favourites", "bop", "bisexual", "pansexual",
    "lana del rey", "lana", "charli xcx", "brat", "charli", "queen of pop",
    "king of pop", "soty", "michael jackson", "lady gaga", "madonna", "beyonce",
    "beautiful", "mother", "bts", "blackpink", "awesome", "bst", "favorite",
    "2016", "korean", "i love", "i like this", "queen", "top songs", "slay",
    "diva", "female vocalist", "confidence", "fav", "forever", "iconic", "love",
    "bot", "bots", "trash", "ass", "flops", "flop", "awful",
    "amor a primeira ouvida", "cunt", "atlas speaks", "nice", "banger",
    "highschool", "colors", "homewrecker", "aoty", "best of 2024", "2024",
    "ariana grande", "this song is for biel", "cheater", "max martin", "mgmt",
    "featuring", "2020", "so good", "shit", "2018",
    "if this were a pokemon i would catch it", "fire", "-1001747063611",
    "my spotify", "sad", "incredible", "flawless", "cried to", "sad asf",
    "heartbreakint", "cried to a lot", "cried completely shitfaced to",
    "so delicate and devastating", "always makes me tear up", "shes mother",
    "mother", "olivia", "test", "jimin", "bts", "bangtan", "paved the way",
    "songs i relate to", "swedish", "best song titles", "radiohead",
    "nicki minaj", "drake", "best", "minhas musicas"
}

def filter_tags(tags):
    return [tag for tag in tags if tag.lower() not in REMOVE_TAGS]

# tag freqs for weights
df['tags_list'] = df['tags'].apply(preprocess_tags)
all_tags = [tag for tags in df['tags_list'] for tag in tags]
tag_freq = Counter(all_tags)
print(f"Tag frequencies loaded: {len(tag_freq)} tags")
