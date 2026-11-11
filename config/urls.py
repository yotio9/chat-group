"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from accounts import views as account_views
from conversations import views as conversation_views
from messaging import views as messaging_views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", account_views.espace_chat, name="home"),
    path("espace_chat/", account_views.espace_chat, name="espace_chat"),
    path("accueil/", account_views.accueil, name="accueil"),
    path("inscription/", account_views.inscription, name="inscription"),
    path("connextion/", account_views.connextion, name="connextion"),
    path("deconnexion/", account_views.deconnexion, name="deconnexion"),
    path("users/", conversation_views.user_directory, name="user_directory"),
    path(
        "conversation/private/",
        conversation_views.start_private_conversation,
        name="start_private_conversation",
    ),
    path(
        "conversation/group/create/",
        conversation_views.create_group_conversation,
        name="create_group_conversation",
    ),
    path("conversation/<int:conversation_id>/", messaging_views.get_messages, name="get_messages"),
    path("conversation/<int:conversation_id>/send/",messaging_views.send_message,name="send_message"),
]