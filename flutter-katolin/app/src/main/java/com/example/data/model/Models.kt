package com.example.data.model

data class Store(
    val id: Int,
    val name: String,
    val category: String,
    val rating: Double,
    val deliveryTime: String,
    val minOrder: String,
    val deliveryFee: String,
    val isOpen: Boolean = true,
    val description: String = "",
    val badge: String = "معتمد",
    val location: String = "صنعاء - شارع الزبيري",
    val phone: String = "771234567",
    val workingHours: String = "9:00 ص - 10:00 م",
    val storeCategories: List<String> = listOf("الكل", "العروض", "جديدنا", "الأكثر طلباً"),
    val logoUrl: String? = null,
    val coverUrl: String? = null
)

data class Product(
    val id: Int,
    val storeId: Int,
    val storeName: String,
    val name: String,
    val description: String,
    val priceYer: Double,
    val originalPriceYer: Double? = null,
    val category: String,
    val subCategory: String = "",
    val brand: String = "",
    val specs: Map<String, String> = emptyMap(),
    val rating: Double = 4.8,
    val inStock: Boolean = true,
    val badge: String? = null,
    val images: List<String> = emptyList(),
    val colors: List<String> = listOf("أسود ملكي", "أزرق تيتانيوم", "فضي فاخر"),
    val sizes: List<String> = listOf("النسخة القياسية", "نسخة المحترفين Pro"),
    val warranty: String = "ضمان سنتين معتمد من المتجر مع استبدال مجاني",
    val hasWarranty: Boolean = true,
    val reviewsCount: Int = 42
)

data class TelecomPackage(
    val id: String,
    val name: String,
    val description: String,
    val priceYer: Double,
    val category: String, // "رصيد", "فوري", "باقات", "جملة", "ريال"
    val operator: String
)

data class CategoryItem(
    val id: String,
    val title: String,
    val iconName: String,
    val productCount: Int,
    val subCategories: List<String> = emptyList(),
    val serverId: Int? = null,
    val parentId: Int? = null
)

data class BannerItem(
    val id: Int,
    val title: String,
    val subtitle: String,
    val discountTag: String,
    val ctaText: String,
    val isElectronics: Boolean = true
)

data class CartItem(
    val product: Product,
    var quantity: Int
)

data class WalletAccount(
    val accountNumber: String,
    val userName: String,
    val phone: String,
    val isVerified: Boolean = true,
    val balanceYer: Double,
    val balanceSar: Double,
    val balanceUsd: Double,
    val points: Int,
    val savingsPocket: Double
)

data class WalletTransaction(
    val id: String,
    val title: String,
    val type: String, // "PURCHASE", "DEPOSIT", "TRANSFER", "BILL", "CASHBACK"
    val amount: Double,
    val currency: String = "ر.ي",
    val date: String,
    val isPositive: Boolean,
    val recipientName: String? = null,
    val recipientPhone: String? = null,
    val referenceCode: String = "REF-2026",
    val status: String = "ناجحة ومكتملة",
    val fee: Double = 0.0,
    val notes: String? = null
)

data class TransferCheckResult(
    val isAllowed: Boolean,
    val recipientName: String? = null,
    val recipientPhone: String = "",
    val amount: Double = 0.0,
    val fee: Double = 0.0,
    val giftId: Int? = null,
    val message: String
)

data class OrderItemDetail(
    val productId: Int? = null,
    val productName: String,
    val quantity: Int,
    val priceYer: Double,
    val category: String = "",
    val subCategory: String = "",
    val storeName: String = ""
)

data class OrderChatMessage(
    val id: String,
    val senderName: String,
    val message: String,
    val time: String,
    val isFromUser: Boolean
)

data class OrderReview(
    val id: String,
    val userName: String,
    val rating: Float,
    val comment: String,
    val date: String
)

data class StoreOrder(
    val id: String,
    val storeName: String,
    val totalAmount: Double,
    val currency: String = "ر.ي",
    val date: String,
    val status: String, // "قيد التجهيز", "في الطريق مع المندوب", "تم التسليم", "ملغي ومسترجع"
    val itemsCount: Int,
    val items: List<OrderItemDetail> = emptyList(),
    val deliveryAddress: String = "صنعاء - شارع حدة",
    val deliveryDriver: String = "الكابتن أحمد الخولاني",
    val driverPhone: String = "770123456",
    val paymentMethod: String = "محفظة جيب الإلكترونية (مدفوع بالكامل)",
    val statusStep: Int = 2, // 0: تم استلام الطلب, 1: قيد التجهيز, 2: في الطريق مع المندوب, 3: تم التسليم, -1: ملغي
    val rating: Float? = null,
    val userReview: String? = null,
    val reviews: List<OrderReview> = emptyList(),
    val chatMessages: List<OrderChatMessage> = emptyList(),
    val orderNotes: String = "",
    val isCancelled: Boolean = false
)

data class AppNotification(
    val id: String,
    val title: String,
    val message: String,
    val time: String,
    val isRead: Boolean = false
)

data class UserSession(
    val phone: String,
    val fullName: String,
    val token: String? = null,
    val isLoggedIn: Boolean = false,
    val governorate: String = "",
    val pointsBalance: Int = 0,
    val role: String = "customer"
) {
    val isVendor: Boolean get() = isLoggedIn && (role.equals("vendor", ignoreCase = true) || role.equals("seller", ignoreCase = true) || role.equals("merchant", ignoreCase = true))
    val isAdmin: Boolean get() = isLoggedIn && (role.equals("admin", ignoreCase = true) || role.equals("manager", ignoreCase = true) || role.equals("staff", ignoreCase = true) || role.equals("superuser", ignoreCase = true))
}

data class WifiCardDenomination(
    val id: String,
    val title: String,         // e.g. "كرت 3 ساعات - 1 جيجا", "كرت 24 ساعة - 5 جيجا"
    val duration: String,      // "3 ساعات", "24 ساعة", "7 أيام", "30 يوم"
    val dataQuota: String,     // "1 GB", "5 GB", "20 GB", "مفتوح"
    val priceYer: Double,      // 100.0, 200.0, 500.0, 1500.0, 3500.0
    val speedLimit: String = "سرعة تصل إلى 20 ميجا فايبر",
    val isPopular: Boolean = false
)

data class WifiNetwork(
    val id: String,
    val name: String,              // اسم شبكة الوايفاي
    val ownerName: String,         // اسم صاحب الشبكة
    val ownerPhone: String,        // رقم صاحبها للتواصل السريع والواتساب
    val location: String,          // موقع الشبكة وتغطيتها
    val governorate: String,       // المحافظة
    val signalStrength: Int = 5,   // 1 - 5
    val isOnline: Boolean = true,
    val description: String = "تغطية ممتازة وسرعة إنترنت فايبر فائقة بدون تقطيع",
    val denominations: List<WifiCardDenomination> = emptyList()
)

data class PurchasedWifiCard(
    val id: String,
    val networkName: String,
    val denominationTitle: String,
    val priceYer: Double,
    val pinCode: String,
    val serialNumber: String,
    val targetPhone: String,
    val purchaseDate: String,
    val duration: String,
    val dataQuota: String,
    val ownerPhone: String
)

data class UserAddress(
    val id: Int,
    val title: String, // "المنزل", "العمل", "المتجر"
    val city: String, // "صنعاء", "عدن", "تعز", "إب", "حضرموت", "الحديدة"
    val district: String, // "حدة", "الأصبحي", "الصافية", "التحرير"
    val street: String,
    val building: String = "",
    val phone: String,
    val isDefault: Boolean = false
) {
    val fullAddress: String
        get() = "$city - $district - $street${if (building.isNotBlank()) " - $building" else ""}"
    val recipientName: String
        get() = title
}

data class SupportTicket(
    val id: String,
    val subject: String,
    val category: String, // "استفسار عن طلب", "مشكلة دفع", "شحن وتوصيل", "شكوى", "اقتراح"
    val status: String, // "مفتوحة", "قيد المعالجة", "تم الرد"
    val date: String,
    val lastMessage: String
)

data class SupportChatMessage(
    val id: String,
    val sender: String,
    val message: String,
    val time: String,
    val isFromUser: Boolean
)

data class VendorPayoutRequest(
    val id: String,
    val amount: Double,
    val currency: String = "ر.ي",
    val reference: String,
    val date: String,
    val status: String // "approved", "paid", "pending", "rejected"
)

data class VendorFinance(
    val vendorName: String,
    val walletBalance: Double,
    val availableBalance: Double,
    val earned: Double,
    val paid: Double,
    val pending: Double,
    val currency: String = "ر.ي"
)

data class CurrencyRate(
    val baseCurrency: String,
    val targetCurrency: String,
    val rate: String
)
