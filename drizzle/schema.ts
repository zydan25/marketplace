import { boolean, int, mysqlEnum, mysqlTable, text, timestamp, varchar } from "drizzle-orm/mysql-core";

/** Core user table backing both Manus OAuth users and phone-based store accounts. */
export const users = mysqlTable("users", {
  id: int("id").autoincrement().primaryKey(),
  openId: varchar("openId", { length: 64 }).notNull().unique(),
  name: text("name"),
  email: varchar("email", { length: 320 }),
  firstName: varchar("firstName", { length: 80 }),
  secondName: varchar("secondName", { length: 80 }),
  thirdName: varchar("thirdName", { length: 80 }),
  familyName: varchar("familyName", { length: 80 }),
  governorate: varchar("governorate", { length: 80 }),
  phone: varchar("phone", { length: 20 }).unique(),
  passwordHash: text("passwordHash"),
  loginMethod: varchar("loginMethod", { length: 64 }),
  role: mysqlEnum("role", ["user", "admin"]).default("user").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
  lastSignedIn: timestamp("lastSignedIn").defaultNow().notNull(),
});

/** Products are created only by an administrator; the store begins with no seeded inventory. */
export const products = mysqlTable("products", {
  id: int("id").autoincrement().primaryKey(),
  productCode: varchar("productCode", { length: 80 }).notNull().unique(),
  name: varchar("name", { length: 255 }).notNull(),
  category: varchar("category", { length: 120 }).notNull(),
  description: text("description").notNull(),
  details: text("details"),
  material: varchar("material", { length: 180 }),
  price: int("price").notNull(),
  discountPercent: int("discountPercent").default(0).notNull(),
  shippingNote: varchar("shippingNote", { length: 255 }),
  isTrending: boolean("isTrending").default(false).notNull(),
  isPublished: boolean("isPublished").default(true).notNull(),
  createdByUserId: int("createdByUserId").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const productImages = mysqlTable("productImages", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  storageKey: varchar("storageKey", { length: 512 }).notNull(),
  url: varchar("url", { length: 1024 }).notNull(),
  sortOrder: int("sortOrder").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const productColors = mysqlTable("productColors", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  name: varchar("name", { length: 80 }).notNull(),
  hex: varchar("hex", { length: 9 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const productSizes = mysqlTable("productSizes", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  label: varchar("label", { length: 80 }).notNull(),
  stock: int("stock").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** يربط الصنف بفئات متعددة كي يظهر في المتجر الرئيسي وصفحات الفئات ذات الصلة. */
export const productCategoryAssignments = mysqlTable("productCategoryAssignments", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  category: varchar("category", { length: 120 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const productTrendTags = mysqlTable("productTrendTags", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  tag: varchar("tag", { length: 120 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const productReviews = mysqlTable("productReviews", {
  id: int("id").autoincrement().primaryKey(),
  productId: int("productId").notNull(),
  userId: int("userId").notNull(),
  rating: int("rating").notNull(),
  body: text("body").notNull(),
  selectedColor: varchar("selectedColor", { length: 80 }),
  selectedSize: varchar("selectedSize", { length: 80 }),
  helpfulCount: int("helpfulCount").default(0).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** حوافز يضيفها المدير إلى حساب عميل محدد، وتبدأ فارغة دون كوبونات جاهزة. */
export const customerRewards = mysqlTable("customerRewards", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  rewardType: mysqlEnum("rewardType", ["gift", "coupon", "order_threshold", "quantity_threshold"]).notNull(),
  title: varchar("title", { length: 180 }).notNull(),
  couponCode: varchar("couponCode", { length: 80 }).unique(),
  discountType: mysqlEnum("discountType", ["fixed", "percent"]).default("fixed").notNull(),
  discountValue: int("discountValue").default(0).notNull(),
  minimumOrderAmount: int("minimumOrderAmount").default(0).notNull(),
  minimumQuantity: int("minimumQuantity").default(0).notNull(),
  giftName: varchar("giftName", { length: 180 }),
  isActive: boolean("isActive").default(true).notNull(),
  assignedByUserId: int("assignedByUserId").notNull(),
  expiresAt: timestamp("expiresAt"),
  usedAt: timestamp("usedAt"),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** الطلبات ومحادثاتها خاصة بصاحب الطلب والإدارة فقط. */
export const orders = mysqlTable("orders", {
  id: int("id").autoincrement().primaryKey(),
  orderCode: varchar("orderCode", { length: 80 }).notNull().unique(),
  userId: int("userId").notNull(),
  status: mysqlEnum("status", ["pending_payment", "payment_proof_sent", "paid_shipping", "cancelled"]).default("pending_payment").notNull(),
  totalAmount: int("totalAmount").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const orderItems = mysqlTable("orderItems", {
  id: int("id").autoincrement().primaryKey(),
  orderId: int("orderId").notNull(),
  productId: int("productId").notNull(),
  productName: varchar("productName", { length: 255 }).notNull(),
  imageUrl: varchar("imageUrl", { length: 1024 }),
  color: varchar("color", { length: 100 }).notNull(),
  size: varchar("size", { length: 100 }).notNull(),
  unitPrice: int("unitPrice").notNull(),
  quantity: int("quantity").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const orderMessages = mysqlTable("orderMessages", {
  id: int("id").autoincrement().primaryKey(),
  orderId: int("orderId").notNull(),
  senderId: int("senderId").notNull(),
  senderRole: mysqlEnum("senderRole", ["customer", "admin", "system"]).notNull(),
  body: text("body"),
  imageStorageKey: varchar("imageStorageKey", { length: 512 }),
  imageUrl: varchar("imageUrl", { length: 1024 }),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const orderNotifications = mysqlTable("orderNotifications", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull(),
  orderId: int("orderId").notNull(),
  title: varchar("title", { length: 180 }).notNull(),
  body: text("body").notNull(),
  isRead: boolean("isRead").default(false).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** إشعارات متجر تسويقية ينشئها المدير ويمكن توجيهها لشرائح محددة من العملاء. */
export const marketingNotifications = mysqlTable("marketingNotifications", {
  id: int("id").autoincrement().primaryKey(),
  title: varchar("title", { length: 180 }).notNull(),
  body: text("body").notNull(),
  imageStorageKey: varchar("imageStorageKey", { length: 512 }),
  imageUrl: varchar("imageUrl", { length: 1024 }),
  productId: int("productId"),
  audienceType: mysqlEnum("audienceType", ["governorate", "single", "selected"]).notNull(),
  governorate: varchar("governorate", { length: 80 }),
  createdByUserId: int("createdByUserId").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});
export const marketingNotificationRecipients = mysqlTable("marketingNotificationRecipients", {
  id: int("id").autoincrement().primaryKey(),
  notificationId: int("notificationId").notNull(),
  userId: int("userId").notNull(),
  isRead: boolean("isRead").default(false).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});
/** إعدادات برنامج الدعوات: يبقى الزر مخفيًا حتى يفعّله المدير. */
export const referralSettings = mysqlTable("referralSettings", {
  id: int("id").autoincrement().primaryKey(),
  isEnabled: boolean("isEnabled").default(false).notNull(),
  updatedByUserId: int("updatedByUserId").notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});
export const referrals = mysqlTable("referrals", {
  id: int("id").autoincrement().primaryKey(),
  inviterUserId: int("inviterUserId").notNull(),
  invitedUserId: int("invitedUserId").notNull().unique(),
  referralCode: varchar("referralCode", { length: 80 }).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const userPreferences = mysqlTable("userPreferences", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().unique(),
  currency: mysqlEnum("currency", ["YER", "SAR", "USD"]).default("YER").notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});
export const pricingSettings = mysqlTable("pricingSettings", {
  id: int("id").autoincrement().primaryKey(),
  outsideIbbMarkupPercent: int("outsideIbbMarkupPercent").default(0).notNull(),
  freeShippingOutsideIbb: boolean("freeShippingOutsideIbb").default(true).notNull(),
  updatedByUserId: int("updatedByUserId").notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});
export const supportConversations = mysqlTable("supportConversations", {
  id: int("id").autoincrement().primaryKey(),
  userId: int("userId").notNull().unique(),
  status: mysqlEnum("status", ["open", "closed"]).default("open").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});
export const supportMessages = mysqlTable("supportMessages", {
  id: int("id").autoincrement().primaryKey(),
  conversationId: int("conversationId").notNull(),
  senderId: int("senderId").notNull(),
  senderRole: mysqlEnum("senderRole", ["customer", "admin"]).notNull(),
  body: text("body").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

/** الشريط العلوي وعناصره تبدأ فارغة ويملؤها المدير فقط. */
export const storefrontTabs = mysqlTable("storefrontTabs", {
  id: int("id").autoincrement().primaryKey(),
  title: varchar("title", { length: 90 }).notNull(),
  searchPlaceholder: varchar("searchPlaceholder", { length: 180 }),
  sortOrder: int("sortOrder").default(0).notNull(),
  isActive: boolean("isActive").default(true).notNull(),
  createdByUserId: int("createdByUserId").notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
  updatedAt: timestamp("updatedAt").defaultNow().onUpdateNow().notNull(),
});

export const storefrontSlides = mysqlTable("storefrontSlides", {
  id: int("id").autoincrement().primaryKey(),
  tabId: int("tabId").notNull(),
  title: varchar("title", { length: 180 }),
  subtitle: varchar("subtitle", { length: 255 }),
  ctaLabel: varchar("ctaLabel", { length: 80 }),
  storageKey: varchar("storageKey", { length: 512 }).notNull(),
  imageUrl: varchar("imageUrl", { length: 1024 }).notNull(),
  sortOrder: int("sortOrder").default(0).notNull(),
  isActive: boolean("isActive").default(true).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export const storefrontCircleSections = mysqlTable("storefrontCircleSections", {
  id: int("id").autoincrement().primaryKey(),
  tabId: int("tabId").notNull(),
  title: varchar("title", { length: 100 }).notNull(),
  targetCategory: varchar("targetCategory", { length: 120 }),
  storageKey: varchar("storageKey", { length: 512 }),
  imageUrl: varchar("imageUrl", { length: 1024 }),
  sortOrder: int("sortOrder").default(0).notNull(),
  isActive: boolean("isActive").default(true).notNull(),
  createdAt: timestamp("createdAt").defaultNow().notNull(),
});

export type User = typeof users.$inferSelect;
export type InsertUser = typeof users.$inferInsert;
export type ProductRow = typeof products.$inferSelect;
export type ProductImageRow = typeof productImages.$inferSelect;
export type ProductColorRow = typeof productColors.$inferSelect;
export type ProductSizeRow = typeof productSizes.$inferSelect;
export type ProductCategoryAssignmentRow = typeof productCategoryAssignments.$inferSelect;
export type ProductTrendTagRow = typeof productTrendTags.$inferSelect;
export type ProductReviewRow = typeof productReviews.$inferSelect;
export type CustomerRewardRow = typeof customerRewards.$inferSelect;
export type OrderRow = typeof orders.$inferSelect;
export type OrderItemRow = typeof orderItems.$inferSelect;
export type OrderMessageRow = typeof orderMessages.$inferSelect;
export type OrderNotificationRow = typeof orderNotifications.$inferSelect;
export type MarketingNotificationRow = typeof marketingNotifications.$inferSelect;
export type MarketingNotificationRecipientRow = typeof marketingNotificationRecipients.$inferSelect;
export type ReferralSettingsRow = typeof referralSettings.$inferSelect;
export type ReferralRow = typeof referrals.$inferSelect;
export type UserPreferenceRow = typeof userPreferences.$inferSelect;
export type PricingSettingsRow = typeof pricingSettings.$inferSelect;
export type SupportConversationRow = typeof supportConversations.$inferSelect;
export type SupportMessageRow = typeof supportMessages.$inferSelect;
export type StorefrontTabRow = typeof storefrontTabs.$inferSelect;
export type StorefrontSlideRow = typeof storefrontSlides.$inferSelect;
export type StorefrontCircleSectionRow = typeof storefrontCircleSections.$inferSelect;
