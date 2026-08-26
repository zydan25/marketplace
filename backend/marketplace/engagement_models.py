from django.conf import settings
from django.db import models
from .models import Product, TimeStampedModel

class Favorite(TimeStampedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="favorites")
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="favorites")
    class Meta:
        constraints=[models.UniqueConstraint(fields=["user","product"],name="uniq_user_product_favorite")]

class ProductComment(TimeStampedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="product_comments")
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="comments")
    body=models.TextField(max_length=1000)
    is_approved=models.BooleanField(default=True)
    parent=models.ForeignKey("self",on_delete=models.CASCADE,null=True,blank=True,related_name="replies")

class PasswordResetRequest(TimeStampedModel):
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="password_reset_requests")
    token_hash=models.CharField(max_length=64,unique=True)
    expires_at=models.DateTimeField()
    used_at=models.DateTimeField(null=True,blank=True)
    requested_phone=models.CharField(max_length=32)
    class Meta:
        indexes=[models.Index(fields=["user","expires_at"])]
