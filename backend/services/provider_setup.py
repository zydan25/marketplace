from django.db import transaction
from django.utils.text import slugify

from .management.commands.provision_sanaacash import provision, provision_links
from .models import MainServiceCategory, ProviderConnection, ProviderLink, Service, ServiceCategory, ServiceDistribution, ServiceField


@transaction.atomic
def _ensure_missing_query_services():
    main = MainServiceCategory.objects.get(slug="التسديدات")
    category = ServiceCategory.objects.get(main_category=main, slug="yemen-mobile", parent=None)
    definitions = [
        ("Yemen Mobile - استعلام الرصيد", "yem-query-balance", "yem-query-balance", "yem_query"),
        ("Yemen Mobile - استعلام الباقات", "yem-query-offers", "yem-query-offers", "yem_offer_query"),
    ]
    services = {}
    for name, code, slug, _ in definitions:
        service, _ = Service.objects.update_or_create(code=code, defaults={"category": category, "name": name, "slug": slugify(slug, allow_unicode=True), "pricing_mode": Service.PricingModes.FIXED, "price": 0, "currency": "YER", "is_active": True})
        ServiceField.objects.update_or_create(service=service, key="mobile", defaults={"label": "رقم يمن موبايل", "field_type": "text", "required": True, "sort_order": 10, "validation": {"min_length": 9, "max_length": 9}})
        services[code] = service
    return services


@transaction.atomic
def create_or_update_sanaacash_provider(*, code, name, userid="", domain_name="", username="", password="", note="", base_url="https://sanaacash.yrbso.net/api/yr/"):
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
            "metadata": {"note": note.strip()} if note.strip() else {},
        },
    )
    if password:
        provider.set_password(password)
        provider.save(update_fields=["password_encrypted", "updated_at"])
    _, _, services = provision()
    provider_links = provision_links(provider, services)
    query_services = _ensure_missing_query_services()
    for service_code, link_code in (("yem-query-balance", "yem_query"), ("yem-query-offers", "yem_offer_query")):
        link = provider_links.get(link_code)
        if link:
            ServiceDistribution.objects.update_or_create(service=query_services[service_code], provider_link=link, defaults={"priority": 100, "is_active": True, "conditions": {}})
    return provider


def distribution_matrix():
    services = list(Service.objects.select_related("category__main_category").filter(is_active=True).order_by("category__main_category__sort_order", "category__sort_order", "sort_order", "id"))
    providers = list(ProviderConnection.objects.filter(is_active=True).prefetch_related("links").order_by("name"))
    distribution = {(row.service_id, row.provider_link_id): row for row in ServiceDistribution.objects.select_related("provider_link").all()}
    links_by_provider = {provider.id: [link for link in provider.links.all() if link.is_active] for provider in providers}
    return services, providers, distribution, links_by_provider
