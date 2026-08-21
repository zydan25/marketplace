from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from .models import StorefrontSection, VendorProfile

class DynamicHomeView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, slug=None):
        if slug:
            vendor = VendorProfile.objects.filter(slug=slug, status="active").first()
            if not vendor:
                return Response({"detail": "المتجر غير موجود"}, status=404)
            sections = StorefrontSection.objects.filter(vendor=vendor, is_visible=True).order_by("sort_order")
        else:
            sections = StorefrontSection.objects.filter(vendor__isnull=True, is_visible=True).order_by("sort_order")
            
        data = []
        for section in sections:
            data.append({
                "id": section.id,
                "type": section.section_type,
                "title": section.title,
                "config": section.config
            })
            
        return Response({"success": True, "data": data})
