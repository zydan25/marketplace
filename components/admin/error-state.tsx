import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminErrorState – Professional error display with retry.
 */
export function AdminErrorState({
  message,
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <View style={styles.container}>
      <View style={styles.iconWrap}>
        <MaterialIcons name="error-outline" size={36} color={Colors.danger} />
      </View>
      <Text style={styles.title}>حدث خطأ</Text>
      <Text style={styles.message}>
        {message ?? "حدث خطأ أثناء تحميل البيانات. تحقق من الاتصال وحاول مرة أخرى."}
      </Text>
      {onRetry ? (
        <TouchableOpacity style={styles.retryBtn} onPress={onRetry}>
          <MaterialIcons name="refresh" size={18} color={Colors.textInverse} />
          <Text style={styles.retryText}>إعادة المحاولة</Text>
        </TouchableOpacity>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    justifyContent: "center",
    paddingVertical: Spacing["4xl"],
    paddingHorizontal: Spacing["3xl"],
    gap: Spacing.sm,
  },
  iconWrap: {
    width: 64,
    height: 64,
    borderRadius: Radius.xl,
    backgroundColor: Colors.dangerLight,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.sm,
  },
  title: {
    color: Colors.text,
    ...Font.cardTitle,
    textAlign: "center",
  },
  message: {
    color: Colors.textSecondary,
    ...Font.caption,
    textAlign: "center",
    lineHeight: 20,
  },
  retryBtn: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    backgroundColor: Colors.primary,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.sm,
    marginTop: Spacing.md,
  },
  retryText: {
    color: Colors.textInverse,
    ...Font.button,
  },
});
