#restapp/decorators.py

from functools import wraps
from django.http import HttpResponseForbidden
from django.shortcuts import redirect

def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles:
                return HttpResponseForbidden("You don't have permission to access this page")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def permission_required(perm):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if not request.user.has_perm(perm):
                return HttpResponseForbidden("You don't have permission to access this page")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator