# helloworld/serializers.py
from rest_framework import serializers

class RecommendationSerializer(serializers.Serializer):
    artist = serializers.CharField()
    name = serializers.CharField()
    #track_id = serializers.IntegerField(required=False)
    track_id = serializers.CharField(required=False)
    url = serializers.CharField(required=False, allow_null=True)
    tags = serializers.ListField(child=serializers.CharField(), required=False)
    similarity_score = serializers.FloatField(required=False)
    match_score = serializers.FloatField(required=False)
    explanation = serializers.CharField(required=False, allow_null=True)
    album_cover = serializers.CharField(required=False, allow_null=True)
    preview = serializers.CharField(required=False, allow_null=True)
