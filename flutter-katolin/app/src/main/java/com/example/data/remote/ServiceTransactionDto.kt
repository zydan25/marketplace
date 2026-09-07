package com.example.data.remote

import com.squareup.moshi.Json

data class ServiceTransactionDto(
    @Json(name = "id") val id: String,
    @Json(name = "service") val service: String? = null,
    @Json(name = "status") val status: String? = null,
    @Json(name = "amount") val amount: String? = null,
    @Json(name = "currency") val currency: String? = null,
    @Json(name = "provider_transid") val providerTransid: Long? = null,
    @Json(name = "provider_transaction_id") val providerTransactionId: String? = null,
    @Json(name = "error_code") val errorCode: String? = null,
    @Json(name = "error_message") val errorMessage: String? = null,
    @Json(name = "created_at") val createdAt: String? = null
)
