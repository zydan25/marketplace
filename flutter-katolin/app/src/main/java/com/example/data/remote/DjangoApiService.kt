package com.example.data.remote

import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Query

/**
 * Django REST Framework API Service for shopik.alattab.site
 */
interface DjangoApiService {

    // 1. Categories
    @GET("categories/")
    suspend fun getCategories(
        @Query("page") page: Int? = null
    ): Response<CategoryListResponse>

    // 2. Vendors (Stores)
    @GET("vendors/")
    suspend fun getVendors(): Response<VendorResponse>

    // 3. Products
    @GET("products/")
    suspend fun getProducts(
        @Query("vendor") vendorId: Int? = null,
        @Query("search") search: String? = null,
        @Query("category") category: String? = null
    ): Response<ProductResponse>

    // 4. Auth
    @POST("auth/login/")
    suspend fun login(
        @Body request: LoginPayload
    ): Response<AuthLoginResponse>

    @POST("auth/register/")
    suspend fun register(
        @Body request: RegisterPayload
    ): Response<AuthLoginResponse>

    @GET("auth/me/")
    suspend fun getProfile(
        @Header("Authorization") token: String
    ): Response<UserDto>

    // 5. Orders
    @GET("orders/")
    suspend fun getOrders(
        @Header("Authorization") token: String
    ): Response<OrderResponse>

    @POST("orders/")
    suspend fun createOrder(
        @Header("Authorization") token: String,
        @Body request: CreateOrderRequest
    ): Response<OrderDto>

    // 6. Notifications
    @GET("notifications/")
    suspend fun getNotifications(
        @Header("Authorization") token: String
    ): Response<NotificationResponse>

    // 7. WiFi Networks & Cards (attempts server calls if endpoint is deployed)
    @GET("wifi-networks/")
    suspend fun getWifiNetworks(): Response<List<Map<String, Any>>>

    @POST("wifi/buy/")
    suspend fun buyWifiCard(
        @Header("Authorization") token: String?,
        @Body request: Map<String, Any>
    ): Response<Map<String, Any>>

    // 8. Wallet & Financial Endpoints
    @GET("wallet/")
    suspend fun getWallet(
        @Header("Authorization") token: String
    ): Response<Map<String, Any>>

    @GET("wallets/")
    suspend fun getWallets(
        @Header("Authorization") token: String
    ): Response<Any>

    @POST("wallet/transfer/")
    suspend fun transfer(
        @Header("Authorization") token: String,
        @Body request: Map<String, Any>
    ): Response<Map<String, Any>>

    @POST("wallet/feed/")
    suspend fun feedAccount(
        @Header("Authorization") token: String?,
        @Body request: Map<String, Any>
    ): Response<Map<String, Any>>

    // 9. Gifts / Transfers Flow (POST /api/gifts/ -> confirm/cancel)
    @GET("gifts/")
    suspend fun getGifts(
        @Header("Authorization") token: String
    ): Response<Any>

    @POST("gifts/")
    suspend fun createGift(
        @Header("Authorization") token: String,
        @Body request: Map<String, Any?>
    ): Response<Map<String, Any>>

    @POST("gifts/{id}/confirm/")
    suspend fun confirmGift(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: Int
    ): Response<Map<String, Any>>

    @POST("gifts/{id}/cancel/")
    suspend fun cancelGift(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: Int
    ): Response<Map<String, Any>>

    // 10. Addresses Management (GET, POST, PUT, DELETE, SET_DEFAULT)
    @GET("addresses/")
    suspend fun getAddresses(
        @Header("Authorization") token: String
    ): Response<Any>

    @POST("addresses/")
    suspend fun createAddress(
        @Header("Authorization") token: String,
        @Body address: Map<String, Any?>
    ): Response<Map<String, Any>>

    @retrofit2.http.PUT("addresses/{id}/")
    suspend fun updateAddress(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: Int,
        @Body address: Map<String, Any?>
    ): Response<Map<String, Any>>

    @retrofit2.http.DELETE("addresses/{id}/")
    suspend fun deleteAddress(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: Int
    ): Response<Unit>

    @POST("addresses/{id}/set_default/")
    suspend fun setDefaultAddress(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: Int
    ): Response<Map<String, Any>>

    // 11. Orders Edit and Cancel
    @retrofit2.http.PATCH("orders/{id}/")
    suspend fun updateOrderDetails(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: String,
        @Body payload: Map<String, Any?>
    ): Response<Map<String, Any>>

    @POST("orders/{id}/cancel/")
    suspend fun cancelOrder(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: String
    ): Response<Map<String, Any>>

    @POST("notifications/{id}/read/")
    suspend fun markNotificationRead(
        @Header("Authorization") token: String,
        @retrofit2.http.Path("id") id: String
    ): Response<Map<String, Any>>
}

data class LoginPayload(
    val phone: String,
    val password: String
)
