from django.db import IntegrityError
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product
from .engagement_models import Favorite, ProductComment

class FavoriteSerializer(serializers.ModelSerializer):
    class Meta:
        model=Favorite; fields=["id","product","created_at"]; read_only_fields=["id","created_at"]
class ProductCommentSerializer(serializers.ModelSerializer):
    user_name=serializers.SerializerMethodField()
    class Meta:
        model=ProductComment; fields=["id","product","user","user_name","body","parent","created_at","updated_at"]; read_only_fields=["id","user","user_name","created_at","updated_at"]
    def get_user_name(self,obj): return obj.user.get_full_name() or obj.user.phone or "عميل"
class FavoriteViewSet(viewsets.ModelViewSet):
    serializer_class=FavoriteSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self): return Favorite.objects.filter(user=self.request.user).select_related("product")
    def perform_create(self,serializer):
        try: serializer.save(user=self.request.user)
        except IntegrityError: raise ValidationError({"product":"المنتج موجود بالفعل في المفضلة."})
    @action(detail=False,methods=["post"],url_path="toggle")
    def toggle(self,request):
        product=Product.objects.filter(pk=request.data.get("product"),is_published=True).first()
        if not product: raise ValidationError({"product":"المنتج غير موجود."})
        item=Favorite.objects.filter(user=request.user,product=product).first()
        if item: item.delete(); return Response({"favorite":False})
        Favorite.objects.create(user=request.user,product=product); return Response({"favorite":True})
class ProductCommentViewSet(viewsets.ModelViewSet):
    serializer_class=ProductCommentSerializer; permission_classes=[IsAuthenticated]
    def get_queryset(self):
        qs=ProductComment.objects.filter(is_approved=True).select_related("user","product")
        product=self.request.query_params.get("product")
        return qs.filter(product_id=product) if product else qs
    def perform_create(self,serializer):
        product=Product.objects.filter(pk=self.request.data.get("product"),is_published=True).first()
        if not product: raise ValidationError({"product":"المنتج غير موجود."})
        serializer.save(user=self.request.user,product=product)
    def perform_update(self,serializer):
        if serializer.instance.user_id!=self.request.user.id: raise ValidationError({"detail":"يمكنك تعديل تعليقك فقط."})
        serializer.save()
    def perform_destroy(self,instance):
        if instance.user_id!=self.request.user.id and not (self.request.user.is_staff or self.request.user.role=="admin"): raise ValidationError({"detail":"لا تملك صلاحية حذف هذا التعليق."})
        instance.delete()
