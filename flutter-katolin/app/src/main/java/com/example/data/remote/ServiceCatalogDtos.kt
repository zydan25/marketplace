package com.example.data.remote

import com.squareup.moshi.Json

data class ServiceCatalogResponse(
    @Json(name = "version") val version: String? = null,
    @Json(name = "categories") val categories: List<ServiceMainCategoryDto> = emptyList()
)

data class ServiceMainCategoryDto(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "slug") val slug: String = "",
    @Json(name = "icon") val icon: String? = null,
    @Json(name = "categories") val categories: List<ServiceCategoryDto> = emptyList()
)

data class ServiceCategoryDto(
    @Json(name = "id") val id: Int,
    @Json(name = "name") val name: String,
    @Json(name = "slug") val slug: String = "",
    @Json(name = "icon") val icon: String? = null,
    @Json(name = "parent_id") val parentId: Int? = null,
    @Json(name = "services") val services: List<ServiceDto> = emptyList(),
    @Json(name = "children") val children: List<ServiceCategoryDto> = emptyList()
)

data class ServicePlanTypeDto(
    @Json(name = "id") val id: Int,
    @Json(name = "code") val code: String,
    @Json(name = "name") val name: String,
    @Json(name = "description") val description: String = "",
    @Json(name = "plan_ids") val planIds: List<Long> = emptyList()
)

data class ServiceDto(
    @Json(name = "id") val id: Int,
    @Json(name = "code") val code: String,
    @Json(name = "name") val name: String,
    @Json(name = "icon") val icon: String? = null,
    @Json(name = "description") val description: String = "",
    @Json(name = "service_kind") val serviceKind: String = "purchase",
    @Json(name = "requires_balance") val requiresBalance: Boolean = false,
    @Json(name = "pricing_mode") val pricingMode: String = "fixed",
    @Json(name = "price") val price: String = "0",
    @Json(name = "currency") val currency: String = "YER",
    @Json(name = "min_amount") val minAmount: String? = null,
    @Json(name = "max_amount") val maxAmount: String? = null,
    @Json(name = "fields") val fields: List<ServiceFieldDto> = emptyList(),
    @Json(name = "items") val items: List<ServiceItemDto> = emptyList(),
    @Json(name = "plan_types") val planTypes: List<ServicePlanTypeDto> = emptyList()
)

data class ServiceFieldDto(
    @Json(name = "key") val key: String,
    @Json(name = "label") val label: String,
    @Json(name = "type") val type: String,
    @Json(name = "required") val required: Boolean = true,
    @Json(name = "secret") val secret: Boolean = false,
    @Json(name = "choices") val choices: List<String> = emptyList(),
    @Json(name = "validation") val validation: Map<String, String> = emptyMap()
)

data class ServiceItemDto(
    @Json(name = "id") val id: Long,
    @Json(name = "type") val type: String,
    @Json(name = "name") val name: String,
    @Json(name = "price") val price: String? = null,
    @Json(name = "currency") val currency: String = "YER",
    @Json(name = "metadata") val metadata: Map<String, String> = emptyMap(),
    @Json(name = "availability") val availability: Map<String, String> = emptyMap()
)

data class ServiceRequestPayload(
    @Json(name = "service_id") val serviceId: Int,
    @Json(name = "item_type") val itemType: String? = null,
    @Json(name = "item_id") val itemId: Long? = null,
    @Json(name = "payload") val payload: Map<String, String?>,
    @Json(name = "idempotency_key") val idempotencyKey: String
)
