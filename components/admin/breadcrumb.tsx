import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Spacing } from "./tokens";

export type BreadcrumbItem = {
  label: string;
  onPress?: () => void;
};

/**
 * AdminBreadcrumb – RTL breadcrumb navigation.
 * Shows the path: الرئيسية > الصفحة > الصفحة الحالية
 */
export function AdminBreadcrumb({ items }: { items: BreadcrumbItem[] }) {
  return (
    <View style={styles.container}>
      {items.map((item, index) => {
        const isLast = index === items.length - 1;
        return (
          <View key={index} style={styles.item}>
            {index > 0 && (
              <MaterialIcons name="chevron-left" size={14} color={Colors.textMuted} />
            )}
            {isLast ? (
              <Text style={styles.current}>{item.label}</Text>
            ) : (
              <TouchableOpacity onPress={item.onPress} hitSlop={6}>
                <Text style={styles.link}>{item.label}</Text>
              </TouchableOpacity>
            )}
          </View>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.xs,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.surfaceAlt,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  item: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 2,
  },
  link: {
    color: Colors.primary,
    ...Font.small,
    fontWeight: "600",
  },
  current: {
    color: Colors.textSecondary,
    ...Font.small,
  },
});
