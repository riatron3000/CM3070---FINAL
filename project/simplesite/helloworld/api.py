# helloworld/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .recommender import generate_recommendations
from .serializers import RecommendationSerializer

class RecommendationAPIView(APIView):
    """
    API endpoint that returns music track recommendations.
    Expects POST data:
    {
        "track_ids": [123, 456],
        "track_popularity": "obscure",  # optional: 'known', 'obscure', 'deepcuts'
        "subgenre": "shoegaze"          # optional
    }
    """

    def get(self, request):
        track_ids = request.query_params.getlist("track_ids")
        track_popularity = request.query_params.get("track_popularity")
        subgenre = request.query_params.get("subgenre")

        if not track_ids:
            return Response({"error": "track_ids is required"}, status=status.HTTP_400_BAD_REQUEST)
        if len(track_ids) > 3:
            return Response({"error": "Maximum of 5 track_ids allowed"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            recs = generate_recommendations(track_ids, track_popularity, subgenre)
            serializer = RecommendationSerializer(recs, many=True)
            return Response(serializer.data)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

