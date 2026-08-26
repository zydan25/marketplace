import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

type BadgeVariant = "success" | "warning" | "danger" | "info" | "muted" | "primary";

const variantMap: Record<BadgeVariant, { bg: string; text: string }> = {
  success: { bg: Colors.successLight, text: Colors.success },
  warning: { bg: Colors.warningLight, text: Colors.warning },
  danger: { bg: Colors.dangerLight, text: Colors.danger },
  info: { bg: Colors.infoLight, text: Colors.info },
  muted: { bg: Colors.surfaceAlt, text: Colors.textSecondary },
  primary: { bg: Colors.primaryLight, text: Colors.primary },
};

/**
 * AdminBadge – Status badge with text, never color-only.
 */
export function AdminBadge({
  label,
  variant = "muted",
}: {
  label: string;
  variant?: BadgeVariant;
}) {
  const colors = variantMap[variant];
  return (
    <View style={[styles.badge, { backgroundColor: colors.bg }]}>
      <Text style={[styles.text, { color: colors.text }]} numberOfLines={1}>
        {label}
      </Text>
    </View>
  );
}

/**
 * Maps common Arabic status strings to badge variants.
 */
export function getStatusVariant(status: string): BadgeVariant {
  const s = status.toLowerCase();
  if (["active", "مفعل", "paid", "مدفوع", "completed", "مكتمل", "delivered", "تم التوصيل"].includes(s))
    return "success";
  if (["pending", "قيد الانتظار", "processing", "قيد المعالجة", "جديد"].includes(s))
    return "warning";
  if (["cancelled", "ملغي", "rejected", "مرفوض", "unpaid", "غير مدفوع"].includes(s))
    return "danger";
  if (["paid_shipping", "شحن"].includes(s)) return "info";
  if (["inactive", "غير مفعل"].includes(s)) return "muted";
  return "muted";
}

const styles = StyleSheet.create({
  badge: {
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.full,
    alignSelf: "flex-start" as const,
  },
  text: {
    ...Font.tiny,
    fontWeight: "700",
  },
});
