#externalapi.py
import requests
import urllib.parse

LASTFM_API_KEY = '58adfbab460a3b3abfed242c2ac17148'


def get_track_tags(artist, track):
    """
    Get tags for a given track from Last.fm.

    Args:
        artist (str): Artist name.
        track (str): Track name.

    Returns:
        list[str]: List of tags.
    """
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'track.gettoptags',
        'artist': artist,
        'track': track,
        'api_key': LASTFM_API_KEY,
        'format': 'json'
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
    except:
        return []

    if 'toptags' in data and 'tag' in data['toptags']:
        return [tag['name'].lower() for tag in data['toptags']['tag']]
    return []

######################################################

def get_top_tracks_by_tag(tag, limit=200, page=1): 
    """
    Get top tracks for a given tag from Last.fm.

    Args:
        tag (str): Music tag 
        limit (int, optional): Number of tracks to fetch per request. Defaults to 200.
        page (int, optional): Page number for pagination. Defaults to 1.

    Returns:
        list[dict]: Track dictionaries list with 'name', 'artist', and 'url'.
    """
    url = "https://ws.audioscrobbler.com/2.0/" 
    params = {
        'method': 'tag.gettoptracks',
        'tag': tag,
        'page': page,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': limit,
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
    except:
        return []

    top_tracks = []
    if 'tracks' in data and 'track' in data['tracks']:
        for t in data['tracks']['track']:
            top_tracks.append({
                'name': t['name'],
                'artist': t['artist']['name'],
                'url': t['url']
            })
    b_half = len(top_tracks) // 2
    return top_tracks[b_half:]

#######################################################    

def get_similar_tracks(artist_name, track_name, fallback_page, limit=20):
    """
    Get similar tracks for a given track from Last.fm.

    Args:
        artist_name (str): Artist name.
        track_name (str): Track name.
        limit (int, optional): Number of similar tracks to fetch. Defaults to 12.

    Returns:
        list[dict]: Track dictionaries list with 'name', 'artist', 'track_mbid', 'artist_mbid', 'image', 'url', 'match_score'.
    """

    spl_start = (fallback_page - 1)
    spl_stop = (spl_start + 6)

    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'track.getsimilar',
        'artist': artist_name,
        'track': track_name,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
        'limit': limit
    }
    try:
        res = requests.get(url, params=params)
        data = res.json()
    except:
        return []

    if 'error' in data:
        return []

    similar_tracks = []
    if 'similartracks' in data and 'track' in data['similartracks']:
        for t in data['similartracks']['track']:
            #print(t)
            similar_tracks.append({
                'name': t['name'],
                'artist': t['artist']['name'],
                'track_mbid': t.get('mbid'),
                'artist_mbid': t['artist'].get('mbid'),
                'image': next((img['#text'] for img in t['image'] if img['size'] == 'medium'), None),
                'url': t['url'],
                'match_score': float(t.get('match', 0.0))
            })

    return similar_tracks[spl_start:spl_stop]

##########################################################

def get_deezer_track_info(track_id):
    """
    Get track information from Deezer by track ID.

    Args:
        track_id (int or str): Deezer track ID.

    Returns:
        dict: Dictionary of track details 'track_id', 'title','track_release', 'artist', 'preview', 'link', 'album', 'album_cover', 'bpm', 'gain'. 
    """
    url = f"https://api.deezer.com/track/{track_id}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()  #  error for bad status
        track = response.json()

        return {
            'track_id': track['id'],
            'title': track['title'],
            'track_release': track['release_date'],
            'artist': track['artist']['name'],
            'preview': track['preview'],
            'link': track['link'],
            'album': track['album']['title'],
            'album_cover': track['album']['cover_big'],
            'bpm': track['bpm'],
            'gain': track['gain']
        }
    except requests.RequestException as e:
        print(f"Error contacting Deezer API: {e}")
        return {}

#############################################################

def get_album_cover(artist, track):
    """
    Get album cover and preview for a track using Deezer (initial) or iTunes fallback.

    Args:
        artist (str): Artist name.
        track (str): Track name.

    Returns:
        dict: Dictionary with 'artist', 'track', 'album_cover', 'preview','source'. 
    """
    def normalize(s):
        return s.lower().strip()

    def get_deezer_album_cover(artist, track):
        url = f"https://api.deezer.com/search?q={track} {artist}"
        n_artist = normalize(artist)
        n_track = normalize(track)

        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()

            for item in data.get('data', []):
                title = item['title'].lower().strip()
                artist_name = item['artist']['name'].lower().strip()
                if n_track in title and n_artist in artist_name:
                    return {
                        'artist': item['artist']['name'],
                        'track': item['title'],
                        'album_cover': item['album']['cover_big'],
                        'preview': item['preview'],
                        'source': 'deezer'
                    }
        except:
            return {}
        return {}

    def get_itunes_album_cover(artist, track):
        query = urllib.parse.quote(f"{artist} {track}")
        url = f"https://itunes.apple.com/search?term={query}&media=music&entity=song&limit=5"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            for item in data.get('results', []):
                return {
                    'artist': item['artistName'],
                    'track': item['trackName'],
                    'album_cover': item['artworkUrl100'],
                    'preview': item['previewUrl'],
                    'source': 'itunes'
                }
        except requests.RequestException as e:
            print(f"Error contacting iTunes API: {e}")
        return {}

    # try deezer first choice
    result = get_deezer_album_cover(artist, track)
    if result:
        return result
    # fallback to iTunes if deezer failed
    return get_itunes_album_cover(artist, track)

###############################################################

def fallback_by_artist_tags(artist_name):
    """
    Get fallback artist tags and similar artists from Last.fm.

    Args:
        artist_name (str): Artist name.

    Returns:
        dict: Dictionary with 'artist_name', 'tags', 'similar' (similar artists).
    """
    url = "https://ws.audioscrobbler.com/2.0/"
    params = {
        'method': 'artist.getinfo',
        'artist': artist_name,
        'api_key': LASTFM_API_KEY,
        'format': 'json',
    }
    try:
        res = requests.get(url, params=params, timeout=5)
        res.raise_for_status()
        response = res.json()

        if "artist" not in response:
            print(f"Response returned no data for '{artist_name}': {response}")
            return {"artist_name": artist_name, "tags": [], "similar": []}

        data = response["artist"]
        artist_name = data.get("name", artist_name)
        tags = [t["name"] for t in data.get("tags", {}).get("tag", [])]
        similar = [t["name"] for t in data.get("similar", {}).get("artist", [])]

        return {"artist_name": artist_name, "tags": tags, "similar": similar}

    except requests.RequestException as e:
        print(f"Request failed for '{artist_name}': {e}")
    except Exception as e:
        print(f"Error for artist '{artist_name}': {e}")



