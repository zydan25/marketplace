from django.core.validators import URLValidator
from django.db import models
from django.core.exceptions import ValidationError


class StorefrontMedia(models.Model):
    name = models.CharField(max_length=180)
    image = models.ImageField(upload_to="storefront/")
    alt_text = models.CharField(max_length=180, blank=True)
    target_url = models.CharField(max_length=500, blank=True)
    vendor = models.ForeignKey("marketplace.VendorProfile", on_delete=models.CASCADE, null=True, blank=True, related_name="storefront_media")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "id"]
        indexes = [models.Index(fields=["vendor", "is_active"])]

    def clean(self):
        if self.target_url.startswith("http"):
            URLValidator()(self.target_url)
        elif self.target_url and not self.target_url.startswith("/"):
            raise ValidationError({"target_url": "استخدم رابطًا داخليًا يبدأ بـ / أو رابط HTTP/HTTPS."})

    def __str__(self):
        return self.name
