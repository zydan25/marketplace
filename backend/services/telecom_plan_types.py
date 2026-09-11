from django.db import models


class TelecomPlanType(models.Model):
    service = models.ForeignKey("Service", on_delete=models.CASCADE, related_name="plan_types")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="children",
    )
    code = models.CharField(max_length=80)
    name = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    sort_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    plans = models.ManyToManyField("TelecomPlan", related_name="plan_types", blank=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [models.UniqueConstraint(fields=["service", "code"], name="uniq_service_plan_type_code")]
        indexes = [
            models.Index(fields=["service", "is_active"], name="svc_plan_type_active_idx"),
            models.Index(fields=["service", "parent", "is_active"], name="svc_plan_type_tree_idx"),
        ]

    def __str__(self):
        return f"{self.service.name} - {self.name}"
