import requests
from django.shortcuts import render
from datetime import datetime


LASTFM_API_KEY = '58adfbab460a3b3abfed242c2ac17148'


def my_view(request):
    return render(request, 'helloworld/full_details.html', {
        'timestamp': datetime.now().timestamp()
    })

#USED BY TEMPLATE
def search_deezer_tracks(request, limit=10):
    """
    Searches upto 3 different tracks using Deezer API.

    Accepts a comma separated query e.g ?query=track1,track2,track3

    Returns:
        A combined list of results of all the tracks.
    """

    if request.method == 'GET':
        query = request.GET.get('query', '')
        if not query:
            return render(request, 'helloworld/search_form.html', {
                'timestamp': datetime.now().timestamp(), 
            })
        
        # limits to first 3 queries regardless incase user sends more
        queries = [q.strip() for q in query.split(',') if q.strip()][:3] 
        search_result = []
        timestamp = datetime.now().timestamp()

        for q in queries:
            url = f"https://api.deezer.com/search?q={q}"
            try:
                response = requests.get(url)
                response.raise_for_status() # requests library exception handling
                data = response.json()
                if data:
                    for track in data['data'][:limit]:
                        search_result.append({
                            'track_id': track['id'],
                            'title': track['title'],
                            'artist': track['artist']['name'],
                            'preview': track['preview'],
                            'link': track['link'],
                            'album': track['album']['title'],
                            'cover': track['album']['cover_medium'],
                            'searched_query': q  
                        })
                else:
                    print(f"No results found for query: {q}")
            # requets library exception handling
            except requests.RequestException as e:
                print(f"Error contacting Deezer API for query '{q}': {e}")
                continue

        return render(request, 'helloworld/search_results.html', {
            'search_result': search_result,
            'timestamp': timestamp,
            'query': query
        })
