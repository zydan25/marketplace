from .catalog_admin_api import CatalogAdminAPIView, CatalogAdminEntityAPIView


class SafeCatalogAdminEntityAPIView(CatalogAdminEntityAPIView):
    """Keep internal exception details out of the administrator-facing HTTP response."""

    def post(self, request, entity):
        response = super().post(request, entity)
        if getattr(response, "status_code", 200) >= 400 and isinstance(getattr(response, "data", None), dict):
            detail = response.data.get("detail")
            if isinstance(detail, str) and detail.startswith("تعذر حفظ العنصر:"):
                response.data["detail"] = "تعذر حفظ العنصر. راجع بيانات العنصر وسجل الخادم للمزيد من التفاصيل."
        return response
