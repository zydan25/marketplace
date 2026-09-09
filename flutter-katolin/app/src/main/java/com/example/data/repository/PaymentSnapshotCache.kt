package com.example.data.repository

import com.example.SessionStore
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceCatalogResponse
import com.example.data.remote.ServiceSettingsResponse
import com.example.data.remote.ServiceTransactionDto
import com.example.data.remote.ServiceTransactionListResponse

/**
 * Local-first cache for the payment network screen.
 * Reads here never touch the network. The screen decides when to sync.
 */
object PaymentSnapshotCache {
    private const val CATALOG = "payment_snapshot.catalog.v1"
    private const val SETTINGS = "payment_snapshot.settings.v1"
    private const val LAST_SYNC = "payment_snapshot.last_sync.v1"
    private const val PHONE_PREFIX = "payment_snapshot.phone."
    private const val REPORTS_PREFIX = "payment_snapshot.reports."
    private const val OP_PREFIX = "payment_snapshot.operation."

    private val moshi = NetworkClient.moshi()
    private val catalogAdapter = moshi.adapter(ServiceCatalogResponse::class.java)
    private val settingsAdapter = moshi.adapter(ServiceSettingsResponse::class.java)
    private val transactionAdapter = moshi.adapter(ServiceTransactionDto::class.java)
    private val reportAdapter = moshi.adapter(ServiceTransactionListResponse::class.java)

    fun saveCatalog(value: ServiceCatalogResponse) = saveJson(CATALOG, catalogAdapter.toJson(value))
    fun loadCatalog(): ServiceCatalogResponse? = loadJson(CATALOG, catalogAdapter)

    fun saveSettings(value: ServiceSettingsResponse) = saveJson(SETTINGS, settingsAdapter.toJson(value))
    fun loadSettings(): ServiceSettingsResponse? = loadJson(SETTINGS, settingsAdapter)

    fun saveLastSync(timestamp: Long = System.currentTimeMillis()) =
        SessionStore.saveLocalString(LAST_SYNC, timestamp.toString())

    fun loadLastSync(): Long? = SessionStore.loadLocalString(LAST_SYNC)?.toLongOrNull()

    fun savePhoneSnapshot(
        phone: String,
        balance: ServiceTransactionDto?,
        advance: ServiceTransactionDto?,
        offers: ServiceTransactionDto?
    ) {
        val key = PHONE_PREFIX + fingerprint(phone)
        saveJson("$key.balance", balance?.let(transactionAdapter::toJson))
        saveJson("$key.advance", advance?.let(transactionAdapter::toJson))
        saveJson("$key.offers", offers?.let(transactionAdapter::toJson))
    }

    fun loadPhoneSnapshot(phone: String): Triple<ServiceTransactionDto?, ServiceTransactionDto?, ServiceTransactionDto?> {
        val key = PHONE_PREFIX + fingerprint(phone)
        return Triple(
            loadJson("$key.balance", transactionAdapter),
            loadJson("$key.advance", transactionAdapter),
            loadJson("$key.offers", transactionAdapter)
        )
    }

    fun saveReports(phone: String, value: ServiceTransactionListResponse) =
        saveJson(REPORTS_PREFIX + fingerprint(phone), reportAdapter.toJson(value))

    fun loadReports(phone: String): ServiceTransactionListResponse? =
        loadJson(REPORTS_PREFIX + fingerprint(phone), reportAdapter)

    fun saveOperation(phone: String, tx: ServiceTransactionDto) =
        saveJson(OP_PREFIX + fingerprint(phone) + "." + tx.id, transactionAdapter.toJson(tx))

    private fun saveJson(key: String, json: String?) {
        SessionStore.saveLocalString(key, json.orEmpty())
    }

    private fun <T> loadJson(key: String, adapter: com.squareup.moshi.JsonAdapter<T>): T? {
        val raw = SessionStore.loadLocalString(key).orEmpty()
        if (raw.isBlank()) return null
        return runCatching { adapter.fromJson(raw) }.getOrNull()
    }

    private fun fingerprint(phone: String): String = phone.filter(Char::isDigit).takeLast(18)
}
