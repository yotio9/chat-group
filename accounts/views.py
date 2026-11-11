from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.db.models import F, Max, Prefetch, Q
from django.db.models.functions import Coalesce
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from conversations.models import ConversationMember
from messaging.models import Message
from .models import User

def accueil(request):
    return render(request, "accueil.html")


def inscription(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password1")

        if not username or not email or not password:
            messages.error(request, "Veuillez remplir tous les champs.")
            return render(request, "inscription.html")

        if password != request.POST.get("password2"):
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return render(request, "inscription.html")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur est déjà utilisé.")
            return render(request, "inscription.html")

        if User.objects.filter(email=email).exists():
            messages.error(request, "Cette adresse email est déjà utilisée.")
            return render(request, "inscription.html")

        User.objects.create_user(username=username, email=email, password=password)
        messages.success(
            request,
            "Inscription réussie ! Vous pouvez maintenant vous connecter.",
        )
        return redirect("inscription")

    return render(request, "inscription.html")


def connextion(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            messages.success(request, "Connexion réussie !")
            next_url = request.POST.get("next")
            if next_url and url_has_allowed_host_and_scheme(
                next_url,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure(),
            ):
                return redirect(next_url)
            return redirect("home")

        messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")

    return render(request, "connextion.html")


@require_POST
def deconnexion(request):
    logout(request)
    return redirect("connextion")


@login_required(login_url="connextion")
def espace_chat(request):
    memberships = ConversationMember.objects.filter(
        user=request.user
    ).select_related(
        "conversation"
    ).prefetch_related(
        Prefetch(
            "conversation__members",
            queryset=ConversationMember.objects.exclude(
                user=request.user
            ).select_related("user"),
            to_attr="other_members"
        ),
        Prefetch(
            "conversation__messages",
            queryset=Message.objects.select_related(
                "sender"
            ).filter(is_deleted=False).order_by("-created_at")[:1],
            to_attr="latest_messages"
        )
    ).annotate(
        last_activity=Coalesce(
            Max(
                "conversation__messages__created_at",
                filter=Q(conversation__messages__is_deleted=False),
            ),
            F("conversation__updated_at"),
        )
    ).order_by("-last_activity", "-conversation_id")
    conversations = [membership.conversation for membership in memberships]

    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by(
        "username", "pk"
    )
    return render(request, "espace_chat.html", {
        "conversations": conversations,
        "directory_users": users,
        "profile_name": request.user.get_full_name().strip() or request.user.username,
    })
