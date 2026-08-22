# Marketplace architecture

## Source of truth

Django + Django REST Framework is the authoritative backend for customer, vendor and admin marketplace data. PostgreSQL is the production database. The Expo/React Native application is a client of this API.

The Node/Express/tRPC/Drizzle code is retained only as `legacy:*` tooling during migration. New Marketplace features must not add business logic to the legacy Node backend.

## Applications

There is one shared Expo codebase with two runtime/build variants:

- `customer`: customer storefront, cart, checkout, orders, notifications, support.
- `vendor`: vendor dashboard, products, inventory, vendor orders, wallet/payouts, storefront design.

The Django admin interface remains the initial administrative control plane. A dedicated admin web interface can consume the same API later without changing domain models.

## Domain boundaries

The core order model represents a customer checkout. Each distinct vendor within that checkout gets a `VendorOrder`. Inventory, shipment status and vendor financial calculations belong to the vendor order, while payment and customer-level totals remain on the parent order.

Prices, discounts, shipping fees, commission and totals are calculated by the server. Client applications send intent (product, variant, quantity, address, payment method), not trusted totals.

## Inventory lifecycle

For payment-required orders, stock is reserved first and committed when the relevant vendor order is delivered/paid. For cash-on-delivery, stock is committed at order placement. Reservation rows are explicit so future payment providers and expiry workers can release inventory safely.

## Security rules

Every mutation must enforce role plus ownership. Public catalog reads are explicit; write access is never inherited from a broad `AllowAny` default. Vendor queries are scoped to the authenticated vendor. Customer orders are scoped to the authenticated customer.

## API conventions

Use `/api/...` Django endpoints, JSON responses, server-side pagination and stable DTO shapes. Add new endpoints to Django, serializers and tests together. Avoid introducing another HTTP client or business-logic backend for the same domain.

## Web-first delivery

Web is the primary integration test target. `pnpm dev` starts Django and Expo web together, with the local Expo client explicitly pointed at `http://127.0.0.1:8000`.

APK builds use the same source and API contracts through the EAS `customer` and `vendor` profiles. No business logic is forked between APKs.
