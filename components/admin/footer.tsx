import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Spacing } from "./tokens";

/**
 * AdminFooter – Copyright footer for admin dashboard.
 */
export function AdminFooter() {
  return (
    <View style={styles.container}>
      <View style={styles.divider} />
      <Text style={styles.text}>
        جميع الحقوق محفوظة © {new Date().getFullYear()} تصميم وبرمجة{" "}
        <Text style={styles.brand}>يمن كود للتقنية</Text>
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: "center",
    paddingVertical: Spacing["2xl"],
    paddingHorizontal: Spacing.lg,
    marginTop: Spacing.lg,
  },
  divider: {
    width: 40,
    height: 3,
    borderRadius: 2,
    backgroundColor: Colors.border,
    marginBottom: Spacing.md,
  },
  text: {
    color: Colors.textMuted,
    ...Font.caption,
    textAlign: "center",
    lineHeight: 20,
  },
  brand: {
    color: Colors.primary,
    fontWeight: "700",
  },
});
