from rest_framework.permissions import BasePermission


class IsVendorOwnerOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and (user.is_staff or user.role in {"vendor", "admin"}))

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(user.is_staff or user.role == "admin" or obj.owner_id == user.id)


class IsVendorApplicantOrAdmin(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(user.is_staff or user.role == "admin" or obj.applicant_id == user.id)
