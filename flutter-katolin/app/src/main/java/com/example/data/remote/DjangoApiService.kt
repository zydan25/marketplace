package com.example.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

/** Django REST API used by the customer application. */
interface DjangoApiService {
    @GET("categories/")
    suspend fun getCategories(@Query("page") page: Int? = null): Response<CategoryListResponse>

    @GET("vendors/")
    suspend fun getVendors(): Response<VendorResponse>

    @GET("products/")
    suspend fun getProducts(
        @Query("vendor") vendorId: Int? = null,
        @Query("search") search: String? = null,
        @Query("category") category: String? = null
    ): Response<ProductResponse>

    @POST("auth/login/")
    suspend fun login(@Body request: LoginPayload): Response<AuthLoginResponse>

    @POST("auth/register/")
    suspend fun register(@Body request: RegisterPayload): Response<AuthLoginResponse>

    @GET("auth/me/")
    suspend fun getProfile(@Header("Authorization") token: String): Response<UserDto>

    @GET("orders/")
    suspend fun getOrders(@Header("Authorization") token: String): Response<OrderResponse>

    @POST("orders/")
    suspend fun createOrder(@Header("Authorization") token: String, @Body request: CreateOrderRequest): Response<OrderDto>

    @GET("notifications/")
    suspend fun getNotifications(@Header("Authorization") token: String): Response<NotificationResponse>

    @GET("services/catalog/")
    suspend fun getServiceCatalog(@Header("Authorization") token: String): Response<ServiceCatalogResponse>

    @POST("services/requests/")
    suspend fun submitServiceRequest(
        @Header("Authorization") token: String,
        @Header("Idempotency-Key") idempotencyKey: String,
        @Body request: ServiceRequestPayload
    ): Response<ServiceTransactionDto>

    @POST("gifts/lookup/")
    suspend fun lookupRecipient(
        @Header("Authorization") token: String,
        @Body request: Map<String, Any?>
    ): Response<Map<String, Any>>

    @GET("v2/services/wifi/networks/")
    suspend fun getWifiNetworksV2(): Response<Map<String, Any>>

    @POST("v2/services/wifi/purchase/")
    suspend fun purchaseWifiCardV2(
        @Header("Authorization") token: String,
        @Body request: Map<String, Any?>
    ): Response<Map<String, Any>>

    @GET("v2/services/wifi/my-cards/")
    suspend fun getMyWifiCardsV2(
        @Header("Authorization") token: String
    ): Response<Map<String, Any>>

    // Legacy WiFi endpoints retained for backward compatibility.
    @GET("wifi-networks/")
    suspend fun getWifiNetworks(): Response<List<Map<String, Any>>>

    @POST("wifi/buy/")
    suspend fun buyWifiCard(@Header("Authorization") token: String?, @Body request: Map<String, Any>): Response<Map<String, Any>>

    @GET("wallet/")
    suspend fun getWallet(@Header("Authorization") token: String): Response<Map<String, Any>>

    @GET("wallets/")
    suspend fun getWallets(@Header("Authorization") token: String): Response<Any>

    @POST("wallet/transfer/")
    suspend fun transfer(@Header("Authorization") token: String, @Body request: Map<String, Any>): Response<Map<String, Any>>

    @POST("wallet/feed/")
    suspend fun feedAccount(@Header("Authorization") token: String?, @Body request: Map<String, Any>): Response<Map<String, Any>>

    @GET("gifts/")
    suspend fun getGifts(@Header("Authorization") token: String): Response<Any>

    @POST("gifts/")
    suspend fun createGift(@Header("Authorization") token: String, @Body request: Map<String, Any?>): Response<Map<String, Any>>

    @POST("gifts/{id}/confirm/")
    suspend fun confirmGift(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: Int): Response<Map<String, Any>>

    @POST("gifts/{id}/cancel/")
    suspend fun cancelGift(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: Int): Response<Map<String, Any>>

    @GET("addresses/")
    suspend fun getAddresses(@Header("Authorization") token: String): Response<Any>

    @POST("addresses/")
    suspend fun createAddress(@Header("Authorization") token: String, @Body address: Map<String, Any?>): Response<Map<String, Any>>

    @retrofit2.http.PUT("addresses/{id}/")
    suspend fun updateAddress(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: Int, @Body address: Map<String, Any?>): Response<Map<String, Any>>

    @retrofit2.http.DELETE("addresses/{id}/")
    suspend fun deleteAddress(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: Int): Response<Unit>

    @POST("addresses/{id}/set_default/")
    suspend fun setDefaultAddress(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: Int): Response<Map<String, Any>>

    @retrofit2.http.PATCH("orders/{id}/")
    suspend fun updateOrderDetails(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: String, @Body payload: Map<String, Any?>): Response<Map<String, Any>>

    @POST("orders/{id}/cancel/")
    suspend fun cancelOrder(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: String): Response<Map<String, Any>>

    @POST("notifications/{id}/read/")
    suspend fun markNotificationRead(@Header("Authorization") token: String, @retrofit2.http.Path("id") id: String): Response<Map<String, Any>>
}

data class LoginPayload(val phone: String, val password: String)