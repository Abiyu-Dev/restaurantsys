from .models import ActivityLog

def log_activity(user, action_type, description, related_model=None, related_id=None, ip_address=None):
    """
    Utility function to log user activities
    
    Args:
        user: User performing the action
        action_type: Type of action (must match ActivityLog.ACTION_TYPES)
        description: Description of the activity
        related_model: Name of the related model (optional)
        related_id: ID of the related object (optional)
        ip_address: IP address of the user (optional)
    """
    return ActivityLog.objects.create(
        user=user,
        action_type=action_type,
        description=description,
        related_model=related_model,
        related_id=related_id,
        ip_address=ip_address
    )

def get_client_ip(request):
    """
    Retrieves the client's IP address from the request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip