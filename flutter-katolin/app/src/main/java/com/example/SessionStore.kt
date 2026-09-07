package com.example

import android.content.Context
import com.example.data.model.UserSession

/** Small app-private persistence layer for the customer session. */
object SessionStore {
    private const val PREFS = "shopik_customer_session"
    private const val TOKEN = "token"
    private const val PHONE = "phone"
    private const val NAME = "full_name"
    private const val GOVERNORATE = "governorate"
    private const val POINTS = "points"
    private const val ROLE = "role"

    fun save(context: Context, session: UserSession) {
        val token = session.token ?: return
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit()
            .putString(TOKEN, token)
            .putString(PHONE, session.phone)
            .putString(NAME, session.fullName)
            .putString(GOVERNORATE, session.governorate)
            .putInt(POINTS, session.pointsBalance)
            .putString(ROLE, session.role)
            .apply()
    }

    fun load(context: Context): UserSession? {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val token = prefs.getString(TOKEN, null)?.takeIf { it.isNotBlank() } ?: return null
        return UserSession(
            phone = prefs.getString(PHONE, "") ?: "",
            fullName = prefs.getString(NAME, "مستخدم") ?: "مستخدم",
            token = token,
            isLoggedIn = true,
            governorate = prefs.getString(GOVERNORATE, "") ?: "",
            pointsBalance = prefs.getInt(POINTS, 0),
            role = prefs.getString(ROLE, "customer") ?: "customer",
        )
    }

    fun clear(context: Context) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE).edit().clear().apply()
    }
}
