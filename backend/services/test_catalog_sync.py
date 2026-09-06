from decimal import Decimal

from django.test import SimpleTestCase

from .catalog_sync import _decimal, _items_from_response, _mapping


class ProviderCatalogMappingTests(SimpleTestCase):
    def test_nested_response_and_alias_mapping(self):
        data = {"data": {"offers": [{"id": "A1", "title": "باقة", "amount": "1500", "qty": "7"}]}}
        rows = _items_from_response(data, "data.offers")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], "A1")

        class Link:
            metadata = {
                "catalog": {
                    "enabled": True,
                    "service_code": "test-service",
                    "item_type": "telecom_plans",
                    "response_path": "data.offers",
                    "fields": {"external_code": ["id"], "name": ["title"], "price": ["amount"], "quantity": ["qty"]},
                }
            }

        catalog, fields = _mapping(Link())
        self.assertTrue(catalog["enabled"])
        self.assertEqual(fields["external_code"], ["id"])
        self.assertEqual(fields["quantity"], ["qty"])

    def test_decimal_is_safe(self):
        self.assertEqual(_decimal("1500.5"), Decimal("1500.50"))
        self.assertEqual(_decimal("not-a-number"), Decimal("0.00"))
