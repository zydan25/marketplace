import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Shadow, Spacing } from "./tokens";

/**
 * AdminStatTrend – Enhanced stat card with trend arrow.
 */
export function AdminStatTrend({
  icon,
  iconColor,
  iconBg,
  label,
  value,
  trend,
  trendDirection,
  sparkline,
  compact,
}: {
  icon: string;
  iconColor?: string;
  iconBg?: string;
  label: string;
  value: string | number;
  trend?: string;
  trendDirection?: "up" | "down" | "neutral";
  sparkline?: number[];
  compact?: boolean;
}) {
  const trendColor =
    trendDirection === "up"
      ? Colors.success
      : trendDirection === "down"
        ? Colors.danger
        : Colors.textMuted;

  const trendIcon =
    trendDirection === "up"
      ? "trending-up"
      : trendDirection === "down"
        ? "trending-down"
        : "trending-flat";

  return (
    <View style={[styles.card, compact && styles.cardCompact]}>
      <View style={styles.topRow}>
        <View style={[styles.iconWrap, { backgroundColor: iconBg ?? Colors.primaryLight }]}>
          <MaterialIcons name={icon as never} size={20} color={iconColor ?? Colors.primary} />
        </View>
        {trend ? (
          <View style={[styles.trendBadge, { backgroundColor: `${trendColor}15` }]}>
            <MaterialIcons name={trendIcon as never} size={12} color={trendColor} />
            <Text style={[styles.trendText, { color: trendColor }]} numberOfLines={1}>
              {trend}
            </Text>
          </View>
        ) : null}
      </View>

      <Text style={styles.label} numberOfLines={1}>{label}</Text>
      <Text style={[styles.value, compact && styles.valueCompact]} numberOfLines={1}>
        {typeof value === "number" ? value.toLocaleString("ar-YE") : value}
      </Text>

      {sparkline && sparkline.length > 1 ? (
        <View style={styles.sparkline}>
          {sparkline.map((v, i) => {
            const max = Math.max(...sparkline, 1);
            const h = Math.max((v / max) * 24, 3);
            return (
              <View
                key={i}
                style={[
                  styles.sparkBar,
                  {
                    height: h,
                    backgroundColor: i === sparkline.length - 1 ? Colors.primary : Colors.border,
                  },
                ]}
              />
            );
          })}
        </View>
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
  cardCompact: {
    padding: Spacing.md,
    minWidth: 100,
  },
  topRow: {
    flexDirection: "row-reverse",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: Spacing.md,
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
  },
  trendBadge: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: 2,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
    borderRadius: Radius.full,
  },
  trendText: {
    ...Font.tiny,
    fontWeight: "700",
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
  valueCompact: {
    fontSize: 17,
    lineHeight: 22,
  },
  sparkline: {
    flexDirection: "row-reverse",
    alignItems: "flex-end",
    gap: 2,
    height: 28,
    marginTop: Spacing.sm,
  },
  sparkBar: {
    flex: 1,
    borderRadius: 2,
    minHeight: 3,
  },
});
