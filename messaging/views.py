from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from conversations.models import ConversationMember
from .models import Message
import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect



@login_required
@require_POST
@csrf_protect
def send_message(request, conversation_id):

    membership = get_object_or_404(
        ConversationMember,
        conversation_id=conversation_id,
        user=request.user
    )

    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse(
            {"error": "Données JSON invalides."},
            status=400
        )

    content = data.get("content", "").strip()

    if not content:
        return JsonResponse(
            {"error": "Le message ne peut pas être vide."},
            status=400
        )

    message = Message.objects.create(
        conversation=membership.conversation,
        sender=request.user,
        content=content
    )

    membership.conversation.save(update_fields=["updated_at"])

    return JsonResponse({
        "success": True,
        "message": {
            "id": message.id,
            "content": message.content,
            "sender": request.user.username,
            "is_mine": True,
            "created_at": message.created_at.strftime("%H:%M"),
            "is_edited": False
        }
    }, status=201)



@login_required
def get_messages(request, conversation_id):

    membership = get_object_or_404(
        ConversationMember,
        conversation_id=conversation_id,
        user=request.user
    )

    messages = Message.objects.filter(
        conversation=membership.conversation,
        is_deleted=False
    ).select_related(
        "sender"
    ).order_by("created_at")

    data = []

    for message in messages:
        data.append({
            "id": message.id,
            "content": message.content,
            "sender": message.sender.username if message.sender else "Utilisateur supprimé",
            "is_mine": message.sender_id == request.user.id,
            "created_at": message.created_at.strftime("%H:%M"),
            "is_edited": message.is_edited,
        })

    return JsonResponse({
        "conversation_id": conversation_id,
        "messages": data
    })


