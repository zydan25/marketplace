from django.db.models import Q
from rest_framework import serializers, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import AllowAny, BasePermission
from rest_framework.response import Response
from rest_framework.views import APIView

from marketplace.models import VendorProfile

from .models import DesignTheme, StorefrontMedia, StorefrontSection


class StorefrontPermission(BasePermission):
    message = "لا تملك صلاحية إدارة واجهة المتجر."

    def has_permission(self, request, view):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return bool(request.user and request.user.is_authenticated and (
            request.user.is_staff or getattr(request.user, "role", None) in {"admin", "vendor"}
        ))

    def has_object_permission(self, request, view, obj):
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        user = request.user
        if user.is_staff or getattr(user, "role", None) == "admin":
            return True
        vendor = getattr(obj, "vendor", None)
        return bool(vendor and vendor.owner_id == user.id)


class ThemeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DesignTheme
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorefrontSection
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class MediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorefrontMedia
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class ThemeViewSet(viewsets.ModelViewSet):
    serializer_class = ThemeSerializer
    permission_classes = [StorefrontPermission]

    def get_queryset(self):
        user = self.request.user
        qs = DesignTheme.objects.select_related("vendor", "owner")
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            return qs.filter(Q(owner=user) | Q(vendor__owner=user) | Q(is_global=True)).distinct()
        return qs.filter(is_global=True, is_active=True)

    def perform_create(self, serializer):
        user = self.request.user
        vendor = None
        if getattr(user, "role", None) == "vendor":
            vendor = VendorProfile.objects.filter(owner=user).first()
            if not vendor:
                raise serializers.ValidationError({"vendor": "لا يوجد متجر مرتبط بهذا الحساب."})
        serializer.save(owner=user, vendor=vendor)

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        theme = self.get_object()
        if theme.vendor_id:
            DesignTheme.objects.filter(vendor_id=theme.vendor_id).exclude(pk=theme.pk).update(is_active=False)
        elif theme.is_global:
            DesignTheme.objects.filter(is_global=True).exclude(pk=theme.pk).update(is_active=False)
        theme.is_active = True
        theme.save(update_fields=["is_active", "updated_at"])
        return Response(ThemeSerializer(theme, context={"request": request}).data)


class SectionViewSet(viewsets.ModelViewSet):
    serializer_class = SectionSerializer
    permission_classes = [StorefrontPermission]

    def get_queryset(self):
        user = self.request.user
        qs = StorefrontSection.objects.select_related("vendor", "owner")
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            return qs.filter(Q(owner=user) | Q(vendor__owner=user)).distinct()
        return qs.filter(is_visible=True).filter(Q(vendor__isnull=True) | Q(vendor__status="active"))

    def perform_create(self, serializer):
        user = self.request.user
        vendor = VendorProfile.objects.filter(owner=user).first() if getattr(user, "role", None) == "vendor" else None
        serializer.save(owner=user, vendor=vendor)

    @action(detail=False, methods=["post"])
    def reorder(self, request):
        ids = request.data.get("ids")
        if not isinstance(ids, list):
            return Response({"detail": "ids يجب أن تكون قائمة."}, status=status.HTTP_400_BAD_REQUEST)
        qs = self.get_queryset()
        for index, item_id in enumerate(ids):
            qs.filter(pk=item_id).update(sort_order=index)
        return Response({"ok": True})


class MediaViewSet(viewsets.ModelViewSet):
    serializer_class = MediaSerializer
    permission_classes = [StorefrontPermission]

    def get_queryset(self):
        user = self.request.user
        qs = StorefrontMedia.objects.select_related("vendor")
        if user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"):
            return qs
        if user.is_authenticated and getattr(user, "role", None) == "vendor":
            return qs.filter(vendor__owner=user)
        return qs.filter(is_active=True).filter(Q(vendor__isnull=True) | Q(vendor__status="active"))

    def perform_create(self, serializer):
        user = self.request.user
        vendor = VendorProfile.objects.filter(owner=user).first() if getattr(user, "role", None) == "vendor" else None
        serializer.save(vendor=vendor)


class PublicStorefrontView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, vendor_slug=None):
        vendor = None
        if vendor_slug:
            vendor = VendorProfile.objects.filter(slug=vendor_slug, status="active").first()
            if not vendor:
                return Response({"detail": "المتجر غير موجود."}, status=status.HTTP_404_NOT_FOUND)
        theme = (DesignTheme.objects.filter(vendor=vendor, is_active=True).first() if vendor else None)
        if not theme:
            theme = DesignTheme.objects.filter(is_global=True, is_active=True).first()
        sections = StorefrontSection.objects.filter(is_visible=True)
        media = StorefrontMedia.objects.filter(is_active=True)
        if vendor:
            sections = sections.filter(Q(vendor=vendor) | Q(vendor__isnull=True))
            media = media.filter(Q(vendor=vendor) | Q(vendor__isnull=True))
        else:
            sections = sections.filter(vendor__isnull=True)
            media = media.filter(vendor__isnull=True)
        return Response({
            "vendor": {"id": vendor.id, "slug": vendor.slug, "name": vendor.store_name} if vendor else None,
            "theme": ThemeSerializer(theme, context={"request": request}).data if theme else None,
            "sections": SectionSerializer(sections.order_by("sort_order", "id"), many=True, context={"request": request}).data,
            "media": MediaSerializer(media.order_by("sort_order", "id"), many=True, context={"request": request}).data,
        })


@api_view(["GET"])
@permission_classes([AllowAny])
def api_info(request):
    return Response({
        "domain": "storefront",
        "version": "2",
        "resources": ["themes", "sections", "media", "public"],
        "contract": "stable-domain-api",
    })
