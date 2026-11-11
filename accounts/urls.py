from . import views
from django.urls import  path



urlpatterns = [
    path("accueil/", views.accueil, name="accueil"),
    path("inscription/", views.inscription, name="inscription"),
    path("connextion/", views.connextion, name="connextion"),
]