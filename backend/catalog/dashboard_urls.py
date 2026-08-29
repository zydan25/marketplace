from django.urls import path

from .dashboard import (
    category_create,
    category_toggle,
    category_update,
    categories,
    image_create,
    image_delete,
    image_primary,
    option_toggle,
    options,
    overview,
    price_group_toggle,
    price_groups,
    product_create,
    product_detail,
    product_publish_toggle,
    product_trend_toggle,
    product_update,
    products,
    products_export_csv,
    variant_create,
    variant_toggle,
)
from .dashboard_actions import products_bulk
from .dashboard_extra import option_update, price_group_update, variant_edit

app_name = "catalog-dashboard"

urlpatterns = [
    path("", overview, name="home"),
    path("categories/", categories, name="categories"),
    path("categories/add/", category_create, name="category-create"),
    path("categories/<int:category_id>/edit/", category_update, name="category-update"),
    path("categories/<int:category_id>/toggle/", category_toggle, name="category-toggle"),
    path("products/", products, name="products"),
    path("products/bulk/", products_bulk, name="products-bulk"),
    path("products/add/", product_create, name="product-create"),
    path("products/export.csv", products_export_csv, name="products-export"),
    path("products/<int:product_id>/", product_detail, name="product-detail"),
    path("products/<int:product_id>/edit/", product_update, name="product-update"),
    path("products/<int:product_id>/publish/", product_publish_toggle, name="product-publish-toggle"),
    path("products/<int:product_id>/trend/", product_trend_toggle, name="product-trend-toggle"),
    path("products/<int:product_id>/variants/add/", variant_create, name="variant-create"),
    path("variants/<int:variant_id>/edit/", variant_edit, name="variant-edit"),
    path("variants/<int:variant_id>/toggle/", variant_toggle, name="variant-toggle"),
    path("products/<int:product_id>/images/add/", image_create, name="image-create"),
    path("images/<int:image_id>/primary/", image_primary, name="image-primary"),
    path("images/<int:image_id>/delete/", image_delete, name="image-delete"),
    path("options/", options, name="options"),
    path("options/<int:option_id>/edit/", option_update, name="option-update"),
    path("options/<int:option_id>/toggle/", option_toggle, name="option-toggle"),
    path("price-groups/", price_groups, name="price-groups"),
    path("price-groups/<int:group_id>/edit/", price_group_update, name="price-group-update"),
    path("price-groups/<int:group_id>/toggle/", price_group_toggle, name="price-group-toggle"),
]