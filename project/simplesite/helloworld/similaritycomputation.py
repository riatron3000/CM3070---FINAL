from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from .utils import wv
from .tagprocessing import tag_freq
import re


def compute_similarity_score(match_score, original_tags, compared_tags):
    if not original_tags or not compared_tags:
        return round(match_score, 4)
    set1 = set(original_tags)
    set2 = set(compared_tags)
    jaccard = len(set1 & set2) / len(set1 | set2)
    final_score = match_score * 0.7 + jaccard * 0.3
    return round(final_score, 4)


# def clean_tag(tag):
#     # lowercase, remove punctuation and  whitespace
#     tag = tag.lower()
#     tag = re.sub(r'[^\w\s]', '', tag) 
#     tag = tag.strip()
#     return tag


# CUSTOM MODEL
def embed_tags3(tags):
    """
    Generates a weighted track level vector for a tracks list of tags 
    using inverse frequency weighting and embedding model.

    Args:
        tags (list[str]): A list of tag strings.

    Returns:
        numpy.ndarray: Representing the weighted average embedding vector.
    """
    vectors = []
    weights = []
    for tag in tags:
        if tag in wv.wv:
            # inverse frequency  and smoothing
            weight = 1 / np.log(tag_freq[tag] + 2)
            vectors.append(wv.wv[tag] * weight)
            weights.append(weight)
    if not vectors:
        return np.zeros(wv.vector_size)
    # divide by sum for magnitude normalisation
    return np.sum(vectors, axis=0) / np.sum(weights)





# FOR CUSTOM MODEL
def tag_similarity(tags1, tags2, alpha=0.4, subgenre=None):
    """
    Computes similarity to assign similarity score between two sets of tags using a weighted (alpha) cosine similarity and Jaccard and optional subgenre boosting.

    Args:
        tags1 (list[str]): Tag list of the seed track.
        tags2 (list[str]): Tag list of the candidate track.
        alpha (float, optional): Weighting factor for influence of cosine and Jaccard in the final score.
        subgenre (str, optional): If provided and present in candidate tag it boosts the final similarity score.

    Returns:
        float: Similarity score in the range 0-1.
    """
    #print("executing tag_similarity")

    vec1 = embed_tags3(tags1).reshape(1, -1)
    vec2 = embed_tags3(tags2).reshape(1, -1)

    semantic_sim = cosine_similarity(vec1, vec2)[0][0]
    jaccard_sim = jaccard_similarity(tags1, tags2)
    combined_sim = alpha * semantic_sim + (1 - alpha) * jaccard_sim

    if subgenre and subgenre in tags2:
        print(f"Selected style '{subgenre}' found in candidate track tags. Boosting similarity score!!!!!!!!!!!!")
        #combined_sim *= 1.15  # +15% boost if candidate has preferred tag
        combined_sim = (1 - 0.15) * combined_sim + 0.15 * 1.0  # weighted blend if subgenre preference matches

    return combined_sim


# Jaccard similarity
def jaccard_similarity(tags1, tags2):
    """
    Compute the Jaccard similarity between two tag sets.

    Args:
        tags1 (list[str]): First list of tags.
        tags2 (list[str]): Second list of tags.

    Returns:
        float: Jaccard similarity score in the range 0-1.
    """
    set1, set2 = set(tags1), set(tags2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


# def normalize(text):
#     # Lowercase, remove punctuation (e.g., '-', '()', etc.), and extra whitespace
#     return re.sub(r'[^\w\s]', '', text.lower()).strip()

