import json

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET, require_POST

from .models import Conversation, ConversationMember


def _read_json(request):
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


def _conversation_response(conversation, user):
    members = list(
        conversation.members.select_related("user").order_by("user__username")
    )
    other_members = [member.user for member in members if member.user_id != user.pk]
    if conversation.type == Conversation.ConversationType.GROUP:
        name = conversation.name
        avatar = ""
    else:
        peer = other_members[0] if other_members else None
        name = (peer.get_full_name().strip() or peer.username) if peer else "Conversation privée"
        avatar = peer.avatar or "" if peer else ""

    return {
        "id": conversation.pk,
        "type": conversation.type,
        "name": name,
        "avatar": avatar,
        "status": (
            f"Groupe · {len(members)} membres"
            if conversation.type == Conversation.ConversationType.GROUP
            else "Conversation privée"
        ),
    }


@login_required
@require_GET
def user_directory(request):
    User = get_user_model()
    query = request.GET.get("q", "").strip()
    try:
        offset = max(int(request.GET.get("offset", "0")), 0)
    except ValueError:
        return JsonResponse({"error": "La pagination est invalide."}, status=400)

    users = User.objects.filter(is_active=True).exclude(pk=request.user.pk)
    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(first_name__icontains=query)
            | Q(last_name__icontains=query)
        )

    page = list(users.order_by("username", "pk")[offset:offset + 50])
    return JsonResponse({
        "users": [
            {
                "id": user.pk,
                "username": user.username,
                "name": user.get_full_name().strip() or user.username,
                "avatar": user.avatar or "",
                "bio": user.bio or "",
            }
            for user in page
        ],
        "next_offset": offset + len(page) if len(page) == 50 else None,
    })


@login_required
@require_POST
def start_private_conversation(request):
    data = _read_json(request)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Le corps de la requête doit être un objet JSON."}, status=400)

    try:
        target_id = int(data.get("user_id"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "Utilisateur cible invalide."}, status=400)

    if target_id == request.user.pk:
        return JsonResponse({"error": "Vous ne pouvez pas démarrer une conversation avec vous-même."}, status=400)

    User = get_user_model()
    with transaction.atomic():
        locked_users = list(
            User.objects.select_for_update()
            .filter(pk__in=sorted((request.user.pk, target_id)), is_active=True)
            .order_by("pk")
        )
        users_by_id = {user.pk: user for user in locked_users}
        if request.user.pk not in users_by_id:
            return JsonResponse({"error": "Votre compte n'est plus disponible."}, status=401)
        if target_id not in users_by_id:
            return JsonResponse({"error": "Utilisateur introuvable."}, status=404)

        pair_key = f"{min(request.user.pk, target_id)}:{max(request.user.pk, target_id)}"
        created = False
        conversation = Conversation.objects.filter(
            type=Conversation.ConversationType.PRIVATE,
            private_pair_key=pair_key,
        ).first()

        if conversation is None:
            candidates = (
                Conversation.objects.filter(
                    type=Conversation.ConversationType.PRIVATE,
                    members__user_id=request.user.pk,
                )
                .filter(members__user_id=target_id)
                .distinct()
                .order_by("pk")
            )
            expected_members = {request.user.pk, target_id}
            for candidate in candidates:
                member_ids = set(
                    candidate.members.values_list("user_id", flat=True)
                )
                if member_ids == expected_members:
                    conversation = candidate
                    break

        if conversation is None:
            try:
                with transaction.atomic():
                    conversation = Conversation.objects.create(
                        type=Conversation.ConversationType.PRIVATE,
                        created_by=request.user,
                        private_pair_key=pair_key,
                    )
                    ConversationMember.objects.bulk_create([
                        ConversationMember(conversation=conversation, user_id=request.user.pk),
                        ConversationMember(conversation=conversation, user_id=target_id),
                    ])
                    created = True
            except IntegrityError:
                conversation = get_object_or_404(
                    Conversation,
                    type=Conversation.ConversationType.PRIVATE,
                    private_pair_key=pair_key,
                )
        elif conversation.private_pair_key != pair_key:
            conversation.private_pair_key = pair_key
            try:
                conversation.save(update_fields=["private_pair_key"])
            except IntegrityError:
                conversation = Conversation.objects.get(
                    type=Conversation.ConversationType.PRIVATE,
                    private_pair_key=pair_key,
                )

    return JsonResponse({
        "success": True,
        "created": created,
        "conversation": _conversation_response(conversation, request.user),
    })


@login_required
@require_POST
def create_group_conversation(request):
    data = _read_json(request)
    if not isinstance(data, dict):
        return JsonResponse({"error": "Le corps de la requête doit être un objet JSON."}, status=400)

    name = data.get("name")
    member_ids = data.get("member_ids")
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 255:
        return JsonResponse({"error": "Le nom du groupe est obligatoire (255 caractères maximum)."}, status=400)
    if not isinstance(member_ids, list):
        return JsonResponse({"error": "La liste des membres est invalide."}, status=400)

    try:
        selected_ids = {int(member_id) for member_id in member_ids}
    except (TypeError, ValueError):
        return JsonResponse({"error": "La liste des membres contient un identifiant invalide."}, status=400)
    selected_ids.discard(request.user.pk)
    if not selected_ids:
        return JsonResponse({"error": "Sélectionnez au moins un autre membre."}, status=400)

    User = get_user_model()
    with transaction.atomic():
        members = list(
            User.objects.select_for_update()
            .filter(pk__in=selected_ids, is_active=True)
            .order_by("pk")
        )
        if {member.pk for member in members} != selected_ids:
            return JsonResponse({"error": "Un ou plusieurs utilisateurs sont introuvables."}, status=404)

        conversation = Conversation.objects.create(
            type=Conversation.ConversationType.GROUP,
            name=name.strip(),
            created_by=request.user,
        )
        ConversationMember.objects.bulk_create([
            ConversationMember(
                conversation=conversation,
                user=request.user,
                role=ConversationMember.MemberRole.ADMIN,
            ),
            *[
                ConversationMember(
                    conversation=conversation,
                    user=member,
                    role=ConversationMember.MemberRole.MEMBER,
                )
                for member in members
            ],
        ])

    return JsonResponse({
        "success": True,
        "conversation": _conversation_response(conversation, request.user),
    }, status=201)


def chat(request):
    return render(request, "chat.html")

def accueil(request):
    return render(request, "accueil.html")
