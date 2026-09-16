from apps.notifications.models import Notification, NotificationType

def notify_user(recipient, title, message, notification_type=NotificationType.SYSTEM, link_url=''):
    """Send an in-app notification to a user."""
    if not recipient:
        return None
    return Notification.objects.create(
        recipient=recipient,
        title=title,
        message=message,
        notification_type=notification_type,
        link_url=link_url
    )

def notify_admins(title, message, notification_type=NotificationType.SYSTEM, link_url=''):
    """Broadcast notification to all active Admins and Super Admins."""
    from apps.accounts.models import User, UserRole
    admins = User.objects.filter(role__in=[UserRole.SUPER_ADMIN, UserRole.ADMIN], status='ACTIVE')
    notifs = []
    for admin in admins:
        notifs.append(Notification(
            recipient=admin,
            title=title,
            message=message,
            notification_type=notification_type,
            link_url=link_url
        ))
    return Notification.objects.bulk_create(notifs)
