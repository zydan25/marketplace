package com.example.data.remote

import com.squareup.moshi.Json

data class ServiceSettingServiceDto(
    @Json(name = "id") val id: Int,
    @Json(name = "code") val code: String = "",
    @Json(name = "name") val name: String = "",
    @Json(name = "slug") val slug: String = "",
    @Json(name = "icon") val icon: String? = null,
    @Json(name = "category_id") val categoryId: Int? = null,
    @Json(name = "category") val category: String? = null,
    @Json(name = "main_category_id") val mainCategoryId: Int? = null,
    @Json(name = "main_category") val mainCategory: String? = null,
    @Json(name = "detail_path") val detailPath: String? = null
)

data class ServiceSettingDto(
    @Json(name = "id") val id: Int,
    @Json(name = "key") val key: String,
    @Json(name = "name") val name: String = "",
    @Json(name = "group") val group: String = "",
    @Json(name = "description") val description: String = "",
    @Json(name = "setting_type") val settingType: String = "",
    @Json(name = "service_id") val serviceId: Int? = null,
    @Json(name = "service") val service: ServiceSettingServiceDto? = null,
    @Json(name = "is_configured") val isConfigured: Boolean = false
)

data class ServiceSettingsResponse(
    @Json(name = "version") val version: String? = null,
    @Json(name = "count") val count: Int = 0,
    @Json(name = "settings") val settings: List<ServiceSettingDto> = emptyList()
)
