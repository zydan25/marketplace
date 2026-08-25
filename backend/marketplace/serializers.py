import base64
import binascii
from django.core.files.base import ContentFile
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
  model=DesignTheme; fields=["id","name","vendor","is_global","is_active","tokens","layout","sections"]; read_only_fields=["id","is_global"]
class CategorySerializer(serializers.ModelSerializer):
 class Meta:
  model=Category; fields=["id","name","slug","image","parent","is_active","sort_order"]
class ProductVariantSerializer(serializers.ModelSerializer):
 id=serializers.IntegerField(required=False); available_stock=serializers.IntegerField(read_only=True); effective_price=serializers.SerializerMethodField()
 class Meta:
  model=ProductVariant; fields=["id","sku","color","size","price_override","available_stock","stock","reserved_stock","is_active","effective_price"]; read_only_fields=["available_stock","effective_price","reserved_stock"]
 def validate(self,attrs):
  stock=attrs.get("stock"); variant_id=attrs.get("id")
  if stock is not None and variant_id:
   current=ProductVariant.objects.filter(id=variant_id).first()
   if current and stock<current.reserved_stock: raise serializers.ValidationError({"stock":"لا يمكن خفض المخزون عن الكمية المحجوزة."})
  return attrs
 def get_effective_price(self,obj): return obj.price_override if obj.price_override is not None else obj.product.effective_price
class ProductSerializer(serializers.ModelSerializer):
 vendor=VendorSerializer(read_only=True); categories=CategorySerializer(many=True,read_only=True); category_ids=serializers.PrimaryKeyRelatedField(queryset=Category.objects.filter(is_active=True),many=True,source="categories",write_only=True,required=False); effective_price=serializers.DecimalField(max_digits=12,decimal_places=2,read_only=True); available_stock=serializers.IntegerField(read_only=True); discount_percent=serializers.IntegerField(read_only=True); main_image_url=serializers.SerializerMethodField(); gallery=serializers.SerializerMethodField(); image_data_urls=serializers.ListField(child=serializers.CharField(),write_only=True,required=False); main_image_data_url=serializers.CharField(write_only=True,required=False,allow_blank=True); keep_image_ids=serializers.ListField(child=serializers.IntegerField(),write_only=True,required=False); delete_image_ids=serializers.ListField(child=serializers.IntegerField(),write_only=True,required=False); variants=ProductVariantSerializer(many=True,required=False)
 class Meta:
  model=Product; fields=["id","vendor","categories","category_ids","sku","name","slug","description","brand","material","shipping_note","return_policy","price","sale_price","effective_price","discount_percent","currency","stock","reserved_stock","available_stock","colors","sizes","hashtags","details","main_image_url","images","gallery","image_data_urls","main_image_data_url","keep_image_ids","delete_image_ids","variants","rating","reviews_count","sold_count","is_published","is_trending"]; read_only_fields=["id","vendor","sku","reserved_stock","available_stock","effective_price","discount_percent","main_image_url","gallery","rating","reviews_count","sold_count"]
 def _absolute(self,value):
  if not value:return None
  request=self.context.get("request"); return value if value.startswith(("http://","https://")) else request.build_absolute_uri(value) if request else value
 def get_main_image_url(self,obj): return self._absolute(obj.main_image.url) if obj.main_image else None
 def get_gallery(self,obj):
  output=[]
  for item in obj.image_items.all(): output.append({"id":item.id,"url":self._absolute(item.image.url),"alt":item.alt_text,"sort_order":item.sort_order,"is_primary":item.is_primary})
  if not output and obj.images:
   for index,value in enumerate(obj.images):
    url=value.get("url") if isinstance(value,dict) else value
    if url: output.append({"id":-index-1,"url":self._absolute(str(url)),"alt":"","sort_order":index,"is_primary":index==0})
  return output
 def _validate_variant_rows(self,rows,instance=None):
  seen_dimensions=set(); seen_skus=set(); existing_by_id={v.id:v for v in instance.variants.all()} if instance else {}
  for row in rows:
   variant_id=row.get("id")
   if variant_id and variant_id not in existing_by_id: raise serializers.ValidationError({"variants":f"الخيار {variant_id} لا ينتمي إلى هذا المنتج."})
   key=(str(row.get("color","")).strip(),str(row.get("size","")).strip())
   if key in seen_dimensions: raise serializers.ValidationError({"variants":"لا يمكن تكرار تركيبة اللون والمقاس داخل المنتج."})
   seen_dimensions.add(key); sku=str(row.get("sku","")).strip()
   if sku and sku in seen_skus: raise serializers.ValidationError({"variants":f"SKU مكرر داخل الطلب: {sku}"})
   seen_skus.add(sku); qs=ProductVariant.objects.filter(sku=sku)
   if variant_id: qs=qs.exclude(pk=variant_id)
   if sku and qs.exists(): raise serializers.ValidationError({"variants":f"SKU مستخدم مسبقًا: {sku}"})
 def _save_data_images(self,product,urls):
  for index,data_url in enumerate(urls or []):
   if not data_url or ";base64," not in data_url: continue
   header,encoded=data_url.split(";base64,",1); extension=header.split("/")[-1].split(";")[0] or "jpg"
   try: content=ContentFile(base64.b64decode(encoded),name=f"product-{product.pk}-{index}.{extension}")
   except (ValueError,binascii.Error): continue
   ProductImage.objects.create(product=product,image=content,sort_order=index,is_primary=index==0)
  if not product.main_image and product.image_items.exists(): product.main_image=product.image_items.first().image; product.save(update_fields=["main_image","updated_at"])
 def create(self,validated_data):
  urls=validated_data.pop("image_data_urls",[]); main_url=validated_data.pop("main_image_data_url",""); variants_data=validated_data.pop("variants",[]); self._validate_variant_rows(variants_data); product=super().create(validated_data)
  for row in variants_data: row.pop("id",None); ProductVariant.objects.create(product=product,**row)
  self._save_data_images(product,([main_url] if main_url else [])+urls); return product
 def update(self,instance,validated_data):
  urls=validated_data.pop("image_data_urls",[]); main_url=validated_data.pop("main_image_data_url",""); keep_value=validated_data.pop("keep_image_ids",None); keep_ids=set(keep_value or []) if keep_value is not None else None; delete_ids=set(validated_data.pop("delete_image_ids",[])); variants_data=validated_data.pop("variants",None)
  if variants_data is not None:self._validate_variant_rows(variants_data,instance=instance)
  product=super().update(instance,validated_data)
  if delete_ids: product.image_items.filter(id__in=delete_ids).delete()
  if keep_ids is not None: product.image_items.exclude(id__in=keep_ids).delete()
  if variants_data is not None:
   existing={v.id:v for v in product.variants.all()}; incoming_ids=set()
   for row in variants_data:
    row=dict(row); variant_id=row.pop("id",None)
    if variant_id:
     variant=existing[variant_id]
     for key,value in row.items(): setattr(variant,key,value)
     variant.is_active=True; variant.save(); incoming_ids.add(variant_id)
    else: incoming=ProductVariant.objects.create(product=product,is_active=True,**row); incoming_ids.add(incoming.id)
   product.variants.exclude(id__in=incoming_ids).update(is_active=False)
  self._save_data_images(product,([main_url] if main_url else [])+urls); return product
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
