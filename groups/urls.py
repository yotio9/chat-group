from . import views
from django.urls import  path



urlpatterns = [
    path('', views.index, name='blog_index'),
    path('article/', views.article, name='blog_article'),
]