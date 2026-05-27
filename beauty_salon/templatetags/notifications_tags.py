from django import template
from beauty_salon.models import Notification

register = template.Library()

@register.simple_tag(takes_context=True)
def unread_notifications_count(context):
    request = context['request']
    user_id = request.session.get('user_id')
    if not user_id:
        return 0
    return Notification.objects.filter(recipient_id=user_id, is_read=False).count()