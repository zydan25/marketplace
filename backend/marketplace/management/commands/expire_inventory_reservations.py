from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from marketplace.models import Product, ProductVariant
from marketplace.marketplace_models import InventoryReservation


class Command(BaseCommand):
    help = "Release active inventory reservations whose expiry time has passed."

    @transaction.atomic
    def handle(self, *args, **options):
        now = timezone.now()
        reservations = (
            InventoryReservation.objects.select_for_update()
            .select_related("product", "variant")
            .filter(status=InventoryReservation.Status.ACTIVE, expires_at__lte=now)
        )
        released = 0
        for reservation in reservations:
            if reservation.variant_id:
                variant: ProductVariant = reservation.variant
                variant.reserved_stock = max(0, variant.reserved_stock - reservation.quantity)
                variant.save(update_fields=["reserved_stock", "updated_at"])
            elif reservation.product_id:
                product: Product = reservation.product
                product.reserved_stock = max(0, product.reserved_stock - reservation.quantity)
                product.save(update_fields=["reserved_stock", "updated_at"])
            reservation.status = InventoryReservation.Status.EXPIRED
            reservation.save(update_fields=["status", "updated_at"])
            released += 1

        self.stdout.write(self.style.SUCCESS(f"Released {released} expired inventory reservations."))
