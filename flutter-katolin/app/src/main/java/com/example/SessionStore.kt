package com.example

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

data class SessionCredentials(val phone: String, val password: String)

/** Encrypted-at-rest persistence for the customer login session. */
object SessionStore {
    private const val PREFS = "shopik_customer_session"
    private const val CIPHERTEXT = "ciphertext"
    private const val IV = "iv"
    private const val KEY_ALIAS = "shopik_customer_session_key"
    private const val TRANSFORMATION = "AES/GCM/NoPadding"

    @Volatile private var appContext: Context? = null

    fun initialize(context: Context) {
        appContext = context.applicationContext
    }

    private fun context(): Context = appContext ?: error("SessionStore.initialize(context) must be called first")

    private fun key(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        val existing = ks.getKey(KEY_ALIAS, null) as? SecretKey
        if (existing != null) return existing
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        generator.init(
            KeyGenParameterSpec.Builder(KEY_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setRandomizedEncryptionRequired(true)
                .build()
        )
        return generator.generateKey()
    }

    fun saveCredentials(phone: String, password: String) {
        val plain = phone.trim() + "\u0000" + password
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key())
        context().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(CIPHERTEXT, Base64.encodeToString(cipher.doFinal(plain.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP))
            .putString(IV, Base64.encodeToString(cipher.iv, Base64.NO_WRAP))
            .apply()
    }

    fun loadCredentials(): SessionCredentials? {
        val prefs = context().getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val ciphertext = prefs.getString(CIPHERTEXT, null) ?: return null
        val iv = prefs.getString(IV, null) ?: return null
        return runCatching {
            val cipher = Cipher.getInstance(TRANSFORMATION)
            cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, Base64.decode(iv, Base64.NO_WRAP)))
            val plain = String(cipher.doFinal(Base64.decode(ciphertext, Base64.NO_WRAP)), Charsets.UTF_8)
            val separator = plain.indexOf('\u0000')
            if (separator <= 0) null else SessionCredentials(plain.substring(0, separator), plain.substring(separator + 1))
        }.getOrNull()
    }

    fun clear() {
        context().getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }
}