from rest_framework.permissions import BasePermission


class IsAdminOrReadOnly(BasePermission):
    """Public reads; writes are restricted to marketplace admins."""

    def has_permission(self, request, view):
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return True
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.role == "admin"))


class IsAuthenticatedRole(BasePermission):
    """Base permission for explicitly allowed user roles."""

    allowed_roles = frozenset()

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.role in self.allowed_roles))


class IsVendorOrAdmin(IsAuthenticatedRole):
    allowed_roles = frozenset({"vendor", "admin"})


class IsCustomer(IsAuthenticatedRole):
    allowed_roles = frozenset({"customer"})
