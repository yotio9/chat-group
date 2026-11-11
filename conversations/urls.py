from . import views
from django.urls import  path



urlpatterns = [
    path('', views.chat, name='home'),
    path('chat/', views.chat, name='chat'),
]