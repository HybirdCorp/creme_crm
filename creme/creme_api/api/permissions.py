from rest_framework.permissions import BasePermission, IsAuthenticated


class TokenPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.token)


class CremeApiPermission(IsAuthenticated):
    def has_permission(self, request, view):
        is_authenticated = super().has_permission(request, view)
        return is_authenticated and request.user.has_perm("creme_api")
