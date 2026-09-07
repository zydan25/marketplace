package com.example

import android.app.Application

class ShopikApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        SessionStore.initialize(this)
    }
}
