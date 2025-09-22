# helloworld/urls.py
from django.urls import path
# from .views import search_song, select_tracks
from . import views
from django.urls import path
from .api import RecommendationAPIView


urlpatterns = [
    #path('', views.homepage, name='homepage'),
    path('', views.search_deezer_tracks, name='search_deezer_tracks'),
    path("api/recommendations/", RecommendationAPIView.as_view(), name="recommendations-api"),
]

