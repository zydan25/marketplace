package com.example.data.remote

import com.squareup.moshi.FromJson
import com.squareup.moshi.JsonReader
import com.squareup.moshi.JsonWriter
import com.squareup.moshi.Moshi
import com.squareup.moshi.ToJson
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.TimeUnit

class FlexibleMapAdapter {
    @FromJson
    fun fromJson(reader: JsonReader): Map<String, String> {
        val map = mutableMapOf<String, String>()
        when (reader.peek()) {
            JsonReader.Token.BEGIN_OBJECT -> {
                reader.beginObject()
                while (reader.hasNext()) {
                    val key = reader.nextName()
                    when (reader.peek()) {
                        JsonReader.Token.STRING -> {
                            val v = reader.nextString()
                            if (v.isNotBlank()) map[key] = v
                        }
                        JsonReader.Token.NUMBER -> {
                            val num = reader.nextDouble()
                            map[key] = if (num % 1.0 == 0.0) num.toLong().toString() else num.toString()
                        }
                        JsonReader.Token.BOOLEAN -> {
                            map[key] = if (reader.nextBoolean()) "نعم" else "لا"
                        }
                        JsonReader.Token.NULL -> {
                            reader.nextNull<Unit>()
                        }
                        else -> reader.skipValue()
                    }
                }
                reader.endObject()
            }
            JsonReader.Token.STRING -> {
                val str = reader.nextString()
                if (str.isNotBlank()) map["تفاصيل"] = str
            }
            JsonReader.Token.NULL -> {
                reader.nextNull<Unit>()
            }
            else -> reader.skipValue()
        }
        return map
    }

    @ToJson
    fun toJson(writer: JsonWriter, value: Map<String, String>?) {
        if (value == null) {
            writer.nullValue()
        } else {
            writer.beginObject()
            value.forEach { (k, v) ->
                writer.name(k).value(v)
            }
            writer.endObject()
        }
    }
}

object NetworkClient {
    private var currentBaseUrl: String = "https://shopik.alattab.site/api/"
    private var cachedService: DjangoApiService? = null

    private val moshi: Moshi by lazy {
        Moshi.Builder()
            .add(FlexibleMapAdapter())
            .addLast(KotlinJsonAdapterFactory())
            .build()
    }

    private val okHttpClient: OkHttpClient by lazy {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .writeTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(logging)
            .build()
    }

    @Synchronized
    fun getApiService(baseUrl: String = currentBaseUrl): DjangoApiService {
        val normalizedUrl = if (baseUrl.endsWith("/")) baseUrl else "$baseUrl/"
        if (cachedService != null && currentBaseUrl == normalizedUrl) {
            return cachedService!!
        }

        currentBaseUrl = normalizedUrl
        val retrofit = Retrofit.Builder()
            .baseUrl(normalizedUrl)
            .client(okHttpClient)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .build()

        val service = retrofit.create(DjangoApiService::class.java)
        cachedService = service
        return service
    }
}
