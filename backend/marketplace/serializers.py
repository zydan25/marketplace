import base64
import binascii
import hashlib
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from rest_framework import serializers
from .models_extended import ProductVariant
from .marketplace_models import VendorApplication
from .models import (Category,Conversation,Coupon,DesignTheme,Message,Notification,Order,OrderItem,Product,ProductImage,StorefrontSection,User,VendorProfile,Wallet,WalletTransaction)

class UserSerializer(serializers.ModelSerializer):
 class Meta:
  model=User; fields=["id","phone","email","first_name","middle_name","third_name","last_name","governorate","role","avatar","points_balance"]; read_only_fields=["id","role"]
class VendorSerializer(serializers.ModelSerializer):
 owner=UserSerializer(read_only=True); logo_url=serializers.SerializerMethodField(); cover_url=serializers.SerializerMethodField()
 class Meta:
  model=VendorProfile; fields=["id","owner","store_name","slug","description","logo_url","cover_url","phone","address","status","commission_percent","settings"]; read_only_fields=["id","slug","status","commission_percent"]
 def get_logo_url(self,obj): return obj.logo.url if obj.logo else None
 def get_cover_url(self,obj): return obj.cover.url if obj.cover else None
class VendorApplicationSerializer(serializers.ModelSerializer):
 class Meta:
  model=VendorApplication; fields=["id","store_name","description","phone","address","documents","status","review_note","created_at","updated_at"]; read_only_fields=["id","status","review_note","created_at","updated_at"]
class DesignThemeSerializer(serializers.ModelSerializer):
 class Meta:
  model=DesignTheme; fields=["id","name","vendor","is_global","is_active","tokens","layout","sections"]; read_only_fields=["id","vendor","is_global"]

 def _persist_data_urls(self, value, theme_id):
  if isinstance(value, list): return [self._persist_data_urls(item, theme_id) for item in value]
  if not isinstance(value, dict): return value
  result = dict(value)
  request = self.context.get("request")
  for key, item in list(result.items()):
   if key in {"imageUrl", "image_url"} and isinstance(item, str) and item.startswith("data:image/") and ";base64," in item:
    try:
     header, encoded = item.split(";base64,", 1); mime = header.split("/", 1)[1].split(";", 1)[0].lower() or "jpeg"
     extension = "jpg" if mime == "jpeg" else mime if mime in {"png", "webp", "gif"} else "jpg"
     raw = base64.b64decode(encoded, validate=True); digest = hashlib.sha256(raw).hexdigest()[:20]
     path = f"themes/{theme_id}/{digest}.{extension}"
     if not default_storage.exists(path): default_storage.save(path, ContentFile(raw))
     url = default_storage.url(path); result[key] = request.build_absolute_uri(url) if request and url.startswith("/") else url
    except (ValueError, binascii.Error, TypeError):
     raise serializers.ValidationError({key: "تعذر حفظ صورة الثيم المرفوعة."})
   else: result[key] = self._persist_data_urls(item, theme_id)
  return result

 def create(self, validated_data):
  validated_data["sections"] = self._persist_data_urls(validated_data.get("sections", []), "new")
  return super().create(validated_data)

 def update(self, instance, validated_data):
  if "sections" in validated_data: validated_data["sections"] = self._persist_data_urls(validated_data["sections"], instance.pk)
  return super().update(instance, validated_data)

class StorefrontSectionSerializer(serializers.ModelSerializer):
 class Meta:
  model=StorefrontSection; fields=["id","title","section_type","vendor","config","sort_order","is_visible"]; read_only_fields=["id"]
class WalletTransactionSerializer(serializers.ModelSerializer):
 class Meta:
  model=WalletTransaction; fields=["id","transaction_type","amount","balance_after","reference","note","metadata","created_at"]; read_only_fields=fields
class WalletSerializer(serializers.ModelSerializer):
 user=UserSerializer(read_only=True); transactions=WalletTransactionSerializer(many=True,read_only=True)
 class Meta:
  model=Wallet; fields=["id","user","balance","currency","is_locked","transactions"]; read_only_fields=["id","balance","is_locked","transactions"]
class CouponSerializer(serializers.ModelSerializer):
 class Meta:
  model=Coupon; fields=["id","code","discount_percent","discount_amount","minimum_order","usage_limit","used_count","starts_at","ends_at","is_active"]; read_only_fields=["used_count"]
class OrderItemSerializer(serializers.ModelSerializer):
 class Meta:
  model=OrderItem; fields=["id","product","vendor","name_snapshot","sku_snapshot","quantity","unit_price","color","size","vendor_total","commission","vendor_net"]; read_only_fields=["id","vendor","name_snapshot","sku_snapshot","unit_price","vendor_total","commission","vendor_net"]
class OrderSerializer(serializers.ModelSerializer):
 items=OrderItemSerializer(many=True,read_only=True); customer=UserSerializer(read_only=True)
 class Meta:
  model=Order; fields=["id","order_number","customer","status","subtotal","shipping_fee","discount","total","currency","shipping_address","payment_method","payment_status","items","created_at","updated_at"]; read_only_fields=["id","order_number","customer","status","subtotal","discount","total","payment_status","items","created_at","updated_at"]
class NotificationSerializer(serializers.ModelSerializer):
 class Meta:
  model=Notification; fields=["id","title","body","image","product","is_read","created_at"]; read_only_fields=["id","created_at"]
class MessageSerializer(serializers.ModelSerializer):
 sender=UserSerializer(read_only=True)
 class Meta:
  model=Message; fields=["id","conversation","sender","body","attachment","is_read","created_at"]; read_only_fields=["id","conversation","sender","is_read","created_at"]
class ConversationSerializer(serializers.ModelSerializer):
 messages=MessageSerializer(many=True,read_only=True)
 class Meta:
  model=Conversation; fields=["id","customer","vendor","order","subject","is_closed","messages","created_at","updated_at"]; read_only_fields=["customer","messages","created_at","updated_at"]

# Compatibility exports: domain serializers are now canonical in their dedicated apps.
from catalog.serializers import CategorySerializer, ProductImageSerializer, ProductSerializer, ProductVariantSerializer
from catalog.serializers import CatalogOptionSerializer, PriceGroupSerializer
from vendors.serializers import VendorSerializer as CanonicalVendorSerializer, VendorApplicationSerializer as CanonicalVendorApplicationSerializer
VendorSerializer = CanonicalVendorSerializer
VendorApplicationSerializer = CanonicalVendorApplicationSerializer
