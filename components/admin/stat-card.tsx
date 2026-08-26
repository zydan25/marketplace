import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Shadow, Spacing } from "./tokens";

/**
 * AdminStatCard – Symmetrical neumorphic stat card.
 * Used in dashboard for key metrics.
 */
export function AdminStatCard({
  icon,
  iconColor,
  iconBg,
  label,
  value,
  trend,
  trendColor,
}: {
  icon: string;
  iconColor?: string;
  iconBg?: string;
  label: string;
  value: string | number;
  trend?: string;
  trendColor?: string;
}) {
  return (
    <View style={styles.card}>
      <View style={[styles.iconWrap, { backgroundColor: iconBg ?? Colors.primaryLight }]}>
        <MaterialIcons
          name={icon as never}
          size={20}
          color={iconColor ?? Colors.primary}
        />
      </View>
      <Text style={styles.label} numberOfLines={1}>
        {label}
      </Text>
      <Text style={styles.value} numberOfLines={1}>
        {value}
      </Text>
      {trend ? (
        <Text
          style={[styles.trend, { color: trendColor ?? Colors.textMuted }]}
          numberOfLines={1}
        >
          {trend}
        </Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    flex: 1,
    minWidth: 140,
    ...Shadow.soft,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.md,
  },
  label: {
    color: Colors.textSecondary,
    ...Font.caption,
    marginBottom: Spacing.xs,
  },
  value: {
    color: Colors.text,
    fontSize: 22,
    fontWeight: "900",
    lineHeight: 28,
    marginBottom: Spacing.xs,
    fontFamily: "Cairo",
  },
  trend: {
    ...Font.small,
  },
});
