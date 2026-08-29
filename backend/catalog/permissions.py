from rest_framework.permissions import BasePermission


class IsCatalogManager(BasePermission):
    message = "إدارة الكتالوج متاحة للتاجر أو الإدارة فقط."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or getattr(user, "role", None) in {"admin", "vendor"}))


class IsCatalogAdmin(BasePermission):
    message = "هذا الإجراء متاح للإدارة فقط."

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))