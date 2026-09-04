package com.example.data.remote

import com.squareup.moshi.Json

data class VendorOwnerDto(
    @Json(name = "id") val id: Int,
    @Json(name = "phone") val phone: String? = null,
    @Json(name = "first_name") val firstName: String? = null,
    @Json(name = "last_name") val lastName: String? = null,
    @Json(name = "governorate") val governorate: String? = null
)

data class VendorDto(
    @Json(name = "id") val id: Int,
    @Json(name = "store_name") val storeName: String,
    @Json(name = "slug") val slug: String? = null,
    @Json(name = "description") val description: String? = null,
    @Json(name = "logo_url") val logoUrl: String? = null,
    @Json(name = "cover_url") val coverUrl: String? = null,
    @Json(name = "phone") val phone: String? = null,
    @Json(name = "address") val address: String? = null,
    @Json(name = "status") val status: String? = null,
    @Json(name = "owner") val owner: VendorOwnerDto? = null
)

data class VendorResponse(
    @Json(name = "count") val count: Int? = null,
    @Json(name = "results") val results: List<VendorDto> = emptyList()
)

data class CategoryDto(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "slug") val slug: String? = null,
    @Json(name = "image") val image: String? = null,
    @Json(name = "parent") val parent: Int? = null,
    @Json(name = "is_active") val isActive: Boolean? = true,
    @Json(name = "sort_order") val sortOrder: Int? = 0,
    @Json(name = "children_count") val childrenCount: Int? = 0,
    @Json(name = "products_count") val productsCount: Int? = 0
)

data class CategoryListResponse(
    @Json(name = "count") val count: Int? = null,
    @Json(name = "next") val next: String? = null,
    @Json(name = "previous") val previous: String? = null,
    @Json(name = "results") val results: List<CategoryDto> = emptyList()
)

data class ProductGalleryDto(
    @Json(name = "id") val id: Int,
    @Json(name = "url") val url: String,
    @Json(name = "is_primary") val isPrimary: Boolean? = false
)

data class ProductColorDto(
    @Json(name = "name") val name: String? = null,
    @Json(name = "hex") val hex: String? = null
)

data class ProductSizeDto(
    @Json(name = "label") val label: String? = null,
    @Json(name = "stock") val stock: Int? = 0
)

data class ProductVariantDto(
    @Json(name = "id") val id: Int? = null,
    @Json(name = "sku") val sku: String? = null,
    @Json(name = "color") val color: String? = null,
    @Json(name = "size") val size: String? = null,
    @Json(name = "price_override") val priceOverride: String? = null,
    @Json(name = "available_stock") val availableStock: Int? = 0,
    @Json(name = "effective_price") val effectivePrice: Double? = null
)

data class ProductDto(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "slug") val slug: String? = null,
    @Json(name = "description") val description: String? = null,
    @Json(name = "brand") val brand: String? = null,
    @Json(name = "material") val material: String? = null,
    @Json(name = "shipping_note") val shippingNote: String? = null,
    @Json(name = "return_policy") val returnPolicy: String? = null,
    @Json(name = "price") val price: String? = null,
    @Json(name = "sale_price") val salePrice: String? = null,
    @Json(name = "effective_price") val effectivePrice: String? = null,
    @Json(name = "discount_percent") val discountPercent: Int? = 0,
    @Json(name = "currency") val currency: String? = "YER",
    @Json(name = "stock") val stock: Int? = 0,
    @Json(name = "available_stock") val availableStock: Int? = 0,
    @Json(name = "main_image_url") val mainImageUrl: String? = null,
    @Json(name = "gallery") val gallery: List<ProductGalleryDto> = emptyList(),
    @Json(name = "colors") val colors: List<ProductColorDto>? = emptyList(),
    @Json(name = "sizes") val sizes: List<ProductSizeDto>? = emptyList(),
    @Json(name = "hashtags") val hashtags: List<String>? = emptyList(),
    @Json(name = "details") val details: Map<String, String>? = null,
    @Json(name = "variants") val variants: List<ProductVariantDto>? = emptyList(),
    @Json(name = "vendor") val vendor: VendorDto? = null,
    @Json(name = "categories") val categories: List<CategoryDto> = emptyList(),
    @Json(name = "rating") val rating: String? = "0.00",
    @Json(name = "reviews_count") val reviewsCount: Int? = 0,
    @Json(name = "is_trending") val isTrending: Boolean? = false
)

data class ProductResponse(
    @Json(name = "count") val count: Int? = null,
    @Json(name = "results") val results: List<ProductDto> = emptyList()
)

data class OrderItemDto(
    @Json(name = "id") val id: Int? = null,
    @Json(name = "product_id") val productId: Int? = null,
    @Json(name = "product_name") val productName: String? = null,
    @Json(name = "product_image") val productImage: String? = null,
    @Json(name = "vendor_name") val vendorName: String? = null,
    @Json(name = "quantity") val quantity: Int = 1,
    @Json(name = "unit_price") val unitPrice: String? = null
)

data class OrderDto(
    @Json(name = "id") val id: Int,
    @Json(name = "order_number") val orderNumber: String? = null,
    @Json(name = "status") val status: String? = null,
    @Json(name = "subtotal") val subtotal: String? = null,
    @Json(name = "shipping_fee") val shippingFee: String? = null,
    @Json(name = "total") val total: String? = null,
    @Json(name = "currency") val currency: String? = "YER",
    @Json(name = "payment_method") val paymentMethod: String? = null,
    @Json(name = "payment_status") val paymentStatus: String? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "items") val items: List<OrderItemDto>? = emptyList()
)

data class OrderResponse(
    @Json(name = "count") val count: Int? = null,
    @Json(name = "results") val results: List<OrderDto> = emptyList()
)

data class NotificationDto(
    @Json(name = "id") val id: Int? = null,
    @Json(name = "title") val title: String? = null,
    @Json(name = "message") val message: String? = null,
    @Json(name = "body") val body: String? = null,
    @Json(name = "created_at") val createdAt: String? = null,
    @Json(name = "is_read") val isRead: Boolean? = false
)

data class NotificationResponse(
    @Json(name = "count") val count: Int? = null,
    @Json(name = "results") val results: List<NotificationDto> = emptyList()
)

data class UserDto(
    @Json(name = "id") val id: Int,
    @Json(name = "phone") val phone: String,
    @Json(name = "first_name") val firstName: String? = null,
    @Json(name = "last_name") val lastName: String? = null,
    @Json(name = "governorate") val governorate: String? = null,
    @Json(name = "role") val role: String? = null,
    @Json(name = "points_balance") val pointsBalance: Int? = 0
)

data class AuthLoginResponse(
    @Json(name = "token") val token: String,
    @Json(name = "user") val user: UserDto
)

data class RegisterPayload(
    @Json(name = "phone") val phone: String,
    @Json(name = "password") val password: String,
    @Json(name = "first_name") val firstName: String? = null,
    @Json(name = "last_name") val lastName: String? = null,
    @Json(name = "governorate") val governorate: String? = null
)

data class CreateOrderItemRequest(
    @Json(name = "product_id") val productId: Int,
    @Json(name = "quantity") val quantity: Int = 1
)

data class CreateOrderRequest(
    @Json(name = "payment_method") val paymentMethod: String = "cod",
    @Json(name = "shipping_address") val shippingAddress: Map<String, String>? = null,
    @Json(name = "items") val items: List<CreateOrderItemRequest>
)
