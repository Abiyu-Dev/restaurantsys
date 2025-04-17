#restapp/mixins.py

from django.core.exceptions import PermissionDenied

class RoleRequiredMixin:
    allowed_roles = []
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if request.user.role not in self.allowed_roles:
            return self.handle_no_permission()
        return super().dispatch(request, *args, **kwargs)
    
    def handle_no_permission(self):
        raise PermissionDenied("You don't have permission to access this page")

class ManagerRequiredMixin(RoleRequiredMixin):
    allowed_roles = ['manager']