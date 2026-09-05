from django.db import transaction

from .management.commands.provision_sanaacash import provision, provision_links
from .models import ProviderConnection, ProviderLink, Service, ServiceDistribution


@transaction.atomic
def create_or_update_sanaacash_provider(*, code, name, userid="", domain_name="", username="", password="", base_url="https://sanaacash.yrbso.net/api/yr/"):
    provider, _ = ProviderConnection.objects.update_or_create(
        code=code,
        defaults={
            "name": name,
            "connection_type": ProviderConnection.Types.SANAACASH,
            "base_url": base_url,
            "userid": userid,
            "domain_name": domain_name,
            "username": username,
            "is_active": True,
        },
    )
    if password:
        provider.set_password(password)
        provider.save(update_fields=["password_encrypted", "updated_at"])
    _, _, services = provision()
    provision_links(provider, services)
    return provider


def distribution_matrix():
    services = list(Service.objects.select_related("category__main_category").filter(is_active=True).order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id"))
    providers = list(ProviderConnection.objects.filter(is_active=True).order_by("name"))
    distribution = {(row.service_id, row.provider_link.provider_id): row for row in ServiceDistribution.objects.select_related("provider_link").all()}
    links = {(row.provider_id, row.id): row for row in ProviderLink.objects.filter(is_active=True)}
    return services, providers, distribution, links
