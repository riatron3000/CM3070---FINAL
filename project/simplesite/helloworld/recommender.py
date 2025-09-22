# your_app/recommender.py
import requests
import time
from .externalapi import *
from .similaritycomputation import *
from .utils import *
from .tagprocessing import *
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed


######################## HELPERS ##########################

def fetch_tracks_for_tags(tags, max_per_tag, page):

    #results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # submit a task: fetch tracks for each tag(first 12) concurrently + map the Future to its tag
        future_to_tag = {executor.submit(get_top_tracks_by_tag, tag, max_per_tag, page): tag for tag in tags}
        all_tracks = []
        # process completed tasks as they finish
        for future in concurrent.futures.as_completed(future_to_tag):
            tag = future_to_tag[future]
            try:
                tag_tracks = future.result()
                print(f"Got {len(tag_tracks)} tracks for tag: {tag}")
                all_tracks.append((tag, tag_tracks))
            except Exception as exc:
                print(f'Error fetching tracks for tag {tag}: {exc}')
    return all_tracks


def filter_unique_tracks(all_tag_tracks):

    seen = set()
    tracks_to_process = []
    # loop through all (tag, track_list) pairs
    for tag, tag_tracks in all_tag_tracks:
        for t in tag_tracks:
            # key from the track's artist and name for each track for keeping track
            key = (t['artist'].lower(), t['name'].lower())
            if key not in seen:
                seen.add(key)
                tracks_to_process.append(t)
    return tracks_to_process


def process_track(t, original_tags, sim_artists, subgenre):

    t_tags = get_track_tags(t['artist'], t['name'])
    matching_tags = [tag for tag in t_tags if tag in original_tags]
    score = tag_similarity(original_tags, t_tags, alpha=0.4, subgenre=subgenre)
    if t['artist'].lower() in sim_artists:
        print(f"{t['artist']} is a similar artist! Score boosted: {score + 0.02}")
        score += 0.015
    return t, score, matching_tags, t_tags



##############################################################
#                  MAIN RECC LOGIC                           #
##############################################################


def recommend_tracks(input_tags_string, track_matrix, tracks_df, top_n=90, subgenre=None):
    """
    Offline tracks recommendation based on input tags.

    Args:
        input_tags_string (str): Comma separated input tags (seed track).
        track_matrix (numpy.ndarray): Matrix track embeddings
        tracks_df (pandas.DataFrame): DataFrame containing track metadata.
        top_n (int, optional): Number of top recommendations to return. 

    Returns:
        pandas.DataFrame: Top-N recommended tracks with their metadata and similarity scores.
    """

    print("executing recommend_tracks")
    top_semantic = 500
    input_tags = [tag.strip().lower() for tag in input_tags_string.split(",") if tag.strip()]
    input_vec = embed_tags3(input_tags) # embed input tags
    
    if np.all(input_vec == 0): # if zero vector:
        print("No embeddings")
        return pd.DataFrame() # return empty dataframe early exit
    # # cosine similarity 
    similarities = cosine_similarity([input_vec], track_matrix).flatten() 
    top_indices = similarities.argsort()[::-1][:top_semantic] # indices of top semantic matches
    combined_scores = [] # stores scores for each track 

    # standard similarity for top semantic matches
    for i in top_indices:
        track_tags = [t.strip().lower() for t in tracks_df.iloc[i]["tags"].split(",") if t.strip()]
        semantic_sim = similarities[i]
        jaccard_sim = jaccard_similarity(input_tags, track_tags)
        combined_sim = 0.4 * semantic_sim + (1 - 0.4) * jaccard_sim
        # subgenre boost optional
        if subgenre and subgenre.lower() in track_tags:
            combined_sim = (1 - 0.15) * combined_sim + 0.15 * 1.0
        combined_scores.append(combined_sim)

    combined_scores = np.array(combined_scores)
    top_final_indices = np.array(top_indices)[combined_scores.argsort()[::-1][:top_n]] # indices of top final matches 

    recommended = tracks_df.iloc[top_final_indices][["track_id", "name", "artist", "tags"]].copy() #  copy() to use independent df of original of only topN. map indice back to df row
    recommended["similarity"] = combined_scores[combined_scores.argsort()[::-1][:top_n]] # add similarity scores to df

    return recommended

#################################################

def generate_explanation(rec_tags, final_score, original_tags, artist_is_similar, input_artist):
    """
    Generate human readable explanation for a recommended track.

    Args:
        rec_tags (list[str] or str): Tags of the recommended track.
        final_score (float or None): Similarity score between the seed and recommended track.
        original_tags (list[str] or str): Tags of the seed track.
        artist_is_similar (bool): Whether similarity relationship exists between the seed and recommended track artists.
        input_artist (str or None): The name of the input artist.

    Returns:
        str: Explanation of why the track was recommended.
    """
    # make sure both inputsare lists
    if isinstance(rec_tags, str):
        rec_tags = rec_tags.split(", ")
    if isinstance(original_tags, str):
        original_tags = original_tags.split(", ")

    shared = list(set(original_tags) & set(rec_tags)) # unique shared tags
    top_tag = rec_tags[0].lower().replace("_", "") if rec_tags else ""

    if final_score is None:  # fallback
        final_score = 0.2
    if not rec_tags:
        return "A wild card based on your pick."

    # CAS1: artist relationship
    if artist_is_similar and input_artist:
        return f" is a similar artist to {input_artist}."

    # CASE 2: high similarity
    if final_score > 0.7:
        if shared:
            if len(shared) == 1:
                extra_tag = next((t for t in rec_tags if t not in shared), None)
                extra_justification = f" and adding {extra_tag}" if extra_tag else ""
                return f"Strong match, sharing {shared[0]} influences{extra_justification}."
            return f"Strong match, sharing {', '.join(shared)} influences."
        return f"Strong match, carrying {', '.join(top_tag)} vibes similar to your picks."
    
    # CASE 3: Medium similarity
    if final_score > 0.4 and final_score <= 0.7:
        if shared:
            return f"Builds on {', '.join(shared)}."
        return f"Related in spirit — blending {top_tag} with your pick."

    # CASE 4: Low similarity
    if final_score <= 0.4:
        return f"A wildcard — leaning into {top_tag} for a fresh twist."

    
#############################################

def gather_track_recommendations(track_id, fallback_page):
    """
    Gathers recommendations for a seed track using artist and tag information. Handles fallback to offline recommendation if online recommendation is insuffiencient.

    Args:
        track_id (str or int): Deezer track ID to fetch recommendations for.

    Returns:
        tuple:
            og_tags (list[str]): Tags for the seed track or artist if track tags are insufficient.
            similar_artists (list[str]): Artists similar to seed artist.
            recs (list[dict]): Recommended tracks with their corresponding metadata and scores.
            artist_name (str): Artist of the seed track.
    """

    # metadata fetch for the seed track(s)
    track_data = get_deezer_track_info(track_id)
    if 'error' in track_data:
        return [], [], []
    
    artist_name = track_data['artist']
    track_name = track_data['title']
    # fallback artist metadata fetch 
    artist_data = fallback_by_artist_tags(artist_name)
    similar_artists = artist_data["similar"]

    # obtain tags for seed track - fallback to artist tags if necessary
    og_tags = get_track_tags(artist_name, track_name)
    if len(og_tags) < 2 or not og_tags:
        og_tags = fallback_by_artist_tags(artist_name).get("tags")
        print("Defaulting to artist tags due to insufficient track tags.")
    og_tags = filter_tags(og_tags) if og_tags else []

    # build reccs of similar tracks (LASTFM)
    recs = []
    similar_tracks = get_similar_tracks(artist_name, track_name, fallback_page)
    if similar_tracks:
        for track in similar_tracks[:16]:
            artist_is_similar = track['artist'].lower() in [a.lower() for a in similar_artists]
            tags = filter_tags(get_track_tags(track['artist'], track['name']))
            final_score = compute_similarity_score(track['match_score'], og_tags, tags)
            recs.append({
                'artist': track['artist'],
                'name': track['name'],
                'url': track['url'],
                'match_score': track['match_score'],
                'image': track['image'],
                'tags': tags[:5],
                'final_score': final_score,
                'explanation': generate_explanation(tags, final_score, og_tags, artist_is_similar, artist_name)
            })
    print(f"Found {len(recs)} direct similar tracks from LASTFM for {artist_name} - {track_name}")
    return og_tags[:12], similar_artists, recs, artist_name

###############################################

def gather_fallback_recommendations(original_tags, sim_artists, fallback_page, subgenre, input_artist):
    """
    Gathers fallback recommendations when primary recommendations are insufficient.

    Args:
        original_tags (list[str]): Tags of the seed track/artist.
        sim_artists (list[str]): Similar artists to seed artist.
        fallback_page (int): Page number for pagination in fallback results.
        subgenre (str or None): Preferred subgenre to prioritise in recommendation selection.
        input_artist (str): Name of the seed artist for use in explanations.

    Returns:
        tuple:
            - get_art (list[dict]): Recommended tracks, their metadata, tags, similarity score and explanation.:
            - has_fallback (bool): True when get_art contains any recommendations.
    """
    print(f"Gathering fallback recommendations for tags: {original_tags}")

    get_art = []
    # using tag metadata of the seed track browse for candidate tracks
    fallback_tracks = fallback_by_tags(original_tags, sim_artists, page=fallback_page, subgenre=subgenre) if original_tags else []
    # fetch for top tracks from similar artists to the input artist
    if fallback_tracks:
        simartist_tracks = simartists_top_tracks(sim_artists, original_tags, subgenre=subgenre)
        get_art.extend(simartist_tracks)
        # build reccs of top tracks from similar artists and retrived tag based candidates
        for track in fallback_tracks[:70]:
            artist_is_similar = track['artist'].lower() in [a.lower() for a in sim_artists]
            get_art.append({
                'artist': track['artist'],
                'name': track['name'],
                'url': track['url'],
                'match_score': None,
                'tags': track.get('candidate_tags', []),
                'all_tags': track.get('tags', []),
                'final_score': track['similarity_score'],
                'explanation': generate_explanation(track.get('candidate_tags', []), track['similarity_score'], original_tags, artist_is_similar, input_artist),
            })
    return get_art, bool(fallback_tracks)

##################################################

def offline_fallback_recommendations(original_tags, top_n=90, popularity=None):
    """
    Generates offline recommendations from a local track embeddings matrix with optional popularity filtering

    Args:
        original_tags (list[str]): Tags from the seed track.
        top_n (int, optional): Maximum number of recommendations to return.
        popularity (str, optional): Popularity tier filter. 

    Returns:
        list[dict]: Recommended tracks with their metadata, similarity score and explanation.
    """

    print(f"OFFLINE RECS triggered with tags: {original_tags}")
    input_tags_string = ", ".join(original_tags)
    # default to full datastet and matrix
    candidate_df = df 
    candidate_matrix = track_matrix 
    # apply popularity filter if specified - applies mask to both df and matrix to consider only rows matching the filter
    if popularity:
        print(f"Popularity filter: {popularity}")
        mask = df["popularity_tier"] == popularity 
        candidate_matrix = track_matrix[mask.values] 
        candidate_df = df[mask].reset_index(drop=True) 
        if candidate_df.empty:
            print("no tracks match this popularity filter")
            return []
    
    # get offline recommendations
    recommended = recommend_tracks(
        input_tags_string,
        candidate_matrix, 
        candidate_df,  
        top_n=top_n
    )
    # convert df to list of dicts for consistency with other recs
    recs = []
    for _, row in recommended.iterrows():
        recs.append({
            'artist': row['artist'],
            'name': row['name'],
            'track_id': row['track_id'],
            'tags': row['tags'],
            'similarity_score': row['similarity'],
            'explanation': generate_explanation(row['tags'], row['similarity'], original_tags, artist_is_similar=False, input_artist=None),
        })
    return recs

#######################################################

def generate_recommendations(track_ids, track_popularity=None, subgenre=None):
    """
    Orchestration function that generates recommendations by delegating to LASTFM direct track similarity, tag based LASTFM fallback or offline fallbacks if needed.

    Args:
        track_ids (list[str | int]): Track id's to seed the recommendation process.
        track_popularity (str, optional): Popularity tier to guide filtering. 
        subgenre (str, optional): Subgenre preference to guide filtering.

    Returns:
        list[dict]: Gathered recommendations with their metadata, tags, similarity score and explanation.
    """
    # assign pagination based on popularity tier
    if track_popularity == 'obscure':
        fallback_page = 16
    elif track_popularity == 'deepcuts':
        fallback_page = 8
    else:
        fallback_page = 1

    all_recommendations = []
    sim_artists = []
    original_tags = []
    get_art = []

    # gather tag data and primary reccs from seed
    for track_id in track_ids:
        og_tags, similar_artists, recs, artist_name = gather_track_recommendations(track_id, fallback_page)
        original_tags.extend(og_tags)
        sim_artists.extend(similar_artists)
        get_art.extend(recs)

    original_tags = list(set(original_tags))
    sim_artists = list(set(sim_artists))

    # gather fallback reccs using tag and similar artist data
    fallback_art, has_fallback = gather_fallback_recommendations(original_tags, sim_artists, fallback_page, subgenre, artist_name)
    get_art.extend(fallback_art)

    # switch to offline recs if online fallbacks are empty
    if not has_fallback and original_tags: 
    #if original_tags: 
        print("🔄 Using offline fallback recommendations.")
        get_art.extend(offline_fallback_recommendations(original_tags, top_n=90, popularity=track_popularity))

    # deduplicate gathered reccs
    seen = set()
    deduped_art = []
    for item in get_art:
        key = (item['artist'], item['name'])
        if key not in seen:
            deduped_art.append(item)
            seen.add(key)

    recs = fetch_album_arts(deduped_art)
    all_recommendations.extend(recs)
    return all_recommendations

####################################################

def fallback_by_tags(original_tags, sim_artists, max_per_tag=200, max_total=400, page=1, subgenre=None):
    min_sim = 0.035
    candidates = []

    limited_tags = original_tags[:32]
    all_tag_tracks = fetch_tracks_for_tags(limited_tags, max_per_tag, page)
    unique_tracks = filter_unique_tracks(all_tag_tracks)

    # CONCURRENCY CODE SOURCED FROM: https://docs.python.org/3/library/concurrent.futures.html
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # submit task to concurently process returned unique tracks and assess result when track/future is completed processing
        futures = [executor.submit(process_track, t, original_tags, sim_artists, subgenre) for t in unique_tracks]
        for future in concurrent.futures.as_completed(futures):
            try:
                t, score, matching_tags, t_tags = future.result()
                if score >= min_sim:
                    candidates.append({
                        'artist': t['artist'],
                        'name': t['name'],
                        'url': t['url'],
                        'match_score': 0.0,
                        'similarity_score': score,
                        'candidate_tags': matching_tags,
                        'tags': t_tags[:8],
                    })
                    if len(candidates) >= max_total:
                        break
            except Exception as e:
                print(f"Error processing track: {e}")
            if len(candidates) >= max_total:
                break

    candidates.sort(key=lambda x: x['similarity_score'], reverse=True) # sort by score DESC
    print("++++++++++++ COMPLETE ++++++++++++++")
    print(len(candidates))
    return candidates


#################################################

def simartists_top_tracks(sim_artists, original_tags, top_n=3, subgenre=None):
    """
    Gets the top tracks for a list of artists similar to the seed track and scores each against the seed tags to establish matches.

    Args:
        sim_artists (list[str]): Artists similar to the seed artist.
        original_tags (list[str]): Tags from the seed track.
        top_n (int, optional): Number of top tracks to fetch per artist. 
        subgenre (str, optional): Subgenre preference to influence scoring. 

    Returns:
        list[dict]: Recommended tracks with their metadata, similarity score and album art and audio previews.
    """
    url = "https://ws.audioscrobbler.com/2.0/"
    results = []

    print(f"BASELINE TAGS FOR COMP: {original_tags}")
    for artist in sim_artists[:2]:
        params = {
            'method': 'artist.gettoptracks',
            'artist': artist,
            'api_key': LASTFM_API_KEY,
            'format': 'json',
            'limit': top_n
        }
        res = requests.get(url, params=params)
        if res.status_code != 200:
            continue

        data = res.json().get("toptracks", {}).get("track", [])
        for track in data[:top_n]:
            track_name = track["name"]
            tags = get_track_tags(artist, track_name)
            if not tags:
                tags = fallback_by_artist_tags(artist)["tags"]
                print(f"Tags: {tags}")
            # compute similarity score against original tags
            score = tag_similarity(original_tags, tags, alpha=0.4, subgenre=subgenre)
            if score >= 0.65:
                track_details = get_album_cover(artist, track_name)
                print(f"{track_name}, {score}")
                results.append({
                    'artist': artist,
                    'name': track_name,
                    'similarity_score': score,
                    'album_cover': track_details.get('album_cover', None),
                    'preview': track_details.get('preview', None)
                })
            time.sleep(0.2)  
    return results

##################################################

def fetch_album_arts(tracks):
    """
    Gets album covers and audio previews for a list of tracks concurrently.

    Args:
        tracks (list[dict]): Track dictionaries list containing 'artist' and 'name'.

    Returns:
        list[dict]: The recommendations track dictionaries list with a audio preview and albuma art added.
    """
    results = []
    future_to_track = {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        for track in tracks:
            # future object containing the track details
            future = executor.submit(get_album_cover, track['artist'], track['name'])
            # making the future the key and the track details the value.
            future_to_track[future] = track # future_to_track[future1] = {'artist': 'Radiohead', 'name': 'Creep'}, future_to_track[future2] = {'artist': 'Beyoncé', 'name': 'Halo'}

        for future in as_completed(future_to_track):
            # for each completed task get the track details
            track = future_to_track[future]
            try:
                result = future.result()  # result is a dict with 'album_cover' and 'preview'
                track['album_cover'] = result.get('album_cover')
                track['preview'] = result.get('preview')
                # eror logging for missing data
                if not track['album_cover'] or not track['preview']:
                    print(f"Cannot fetch art for: {track['artist']} - {track['name']}")

            except Exception as e:
                print(f"Error fetch album art for {track['artist']} - {track['name']}: {e}")
                track['album_art'] = None
            results.append(track)
        return results







# def fallback_by_tags(original_tags, sim_artists, max_per_tag=200, max_total=400, page=1, subgenre=None): # OG maxpertag=150, maxtotal=230
#     min_sim = 0.035
#     candidates = []
#     seen = set()
#     limited_tags = original_tags[:32]

#     # CONCURRENCY CODE SOURCED FROM: https://docs.python.org/3/library/concurrent.futures.html
#     # submit a task: fetch tracks for each tag(first 12) concurrently + map the Future to its tag
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         future_to_tag = {executor.submit(get_top_tracks_by_tag, tag, max_per_tag, page): tag for tag in limited_tags}
#         all_tag_tracks = []
#         # process completed tasks as they finish
#         for future in concurrent.futures.as_completed(future_to_tag):
#             tag = future_to_tag[future] # map future back to its tag
#             try:
#                 tag_tracks = future.result() # get list of tracks for each tag
#                 print(f"Got {len(tag_tracks)} tracks for tag: {tag}")
#                 all_tag_tracks.append((tag, tag_tracks)) # store tag with tracks (tag, [track1, track2,...])
#             except Exception as exc:
#                 print(f'Error fetching tracks for tag {tag}: {exc}')

#     # concurrently process for tags + score filtering 
#     tracks_to_process = []
#     # loop through all (tag, track_list) pairs
#     for tag, tag_tracks in all_tag_tracks:
#         # create key from the track's artist and name for each track
#         for t in tag_tracks:
#             key = (t['artist'].lower(), t['name'].lower())
#             if key not in seen:
#                 seen.add(key)
#                 tracks_to_process.append(t)

#     # helper to concurrently get track tags and compute score for unique tracks
#     def process_track(t):
#         t_tags = get_track_tags(t['artist'], t['name'])
#         matching_tags = [tag for tag in t_tags if tag in original_tags] #   filter t_tags to only include tags that are in original_tags. this is gonna be used in recc explanations to users 
#         score = tag_similarity(original_tags, t_tags, alpha=0.4, subgenre=subgenre)
#         if t['artist'].lower() in sim_artists: # apply score boost if artist is similar to input artist
#             print(f"============{t['artist']} is a similar artist! Score upgraded!! NEW SCORE: {score + 0.02}=============")
#             score += 0.015
#         return (t, score, matching_tags, t_tags)

#     # process tracks concurrently and collect reccs
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         # submit task to concurently process tracks 
#         futures = [executor.submit(process_track, t) for t in tracks_to_process]
#         # evaluate the result when track/future completes processing
#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 t, score, matching_tags, t_tags = future.result() 
#                 if score >= min_sim:
#                     candidates.append({
#                         'artist': t['artist'],
#                         'name': t['name'],
#                         'url': t['url'],
#                         'match_score': 0.0,
#                         'similarity_score': score,
#                         'candidate_tags': matching_tags,
#                         'tags': t_tags[:8],  
#                     })
#                     if len(candidates) >= max_total:
#                         break
#             except Exception as e:
#                 print(f"Error processing track: {e}")
#             if len(candidates) >= max_total:
#                 break
#     # sort by similarity score descending
#     candidates.sort(key=lambda x: x['similarity_score'], reverse=True)
#     print("++++++++++++ COMPLETE ++++++++++++++")
#     print(len(candidates))
#     return candidates


