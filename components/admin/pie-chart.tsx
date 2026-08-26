import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

type PieData = {
  label: string;
  value: number;
  color: string;
};

/**
 * AdminPieChart – Simple pie chart using colored bar visualization.
 * Pure React Native Views – no external deps.
 */
export function AdminPieChart({
  data,
  title,
}: {
  data: PieData[];
  title?: string;
}) {
  const total = data.reduce((s, d) => s + d.value, 0);
  if (total === 0) return null;

  return (
    <View style={styles.container}>
      {title ? <Text style={styles.title}>{title}</Text> : null}

      {/* Bar visualization */}
      <View style={styles.barRow}>
        {data.map((seg, i) => {
          const pct = Math.max((seg.value / total) * 100, 3);
          return (
            <View
              key={i}
              style={[
                styles.segment,
                {
                  flex: pct,
                  backgroundColor: seg.color || Colors.textMuted,
                },
              ]}
            />
          );
        })}
      </View>

      <View style={styles.totalRow}>
        <Text style={styles.totalLabel}>المجموع</Text>
        <Text style={styles.totalValue}>{total.toLocaleString("ar-YE")}</Text>
      </View>

      {/* Legend */}
      <View style={styles.legend}>
        {data.map((seg, i) => {
          const pct = total > 0 ? Math.round((seg.value / total) * 100) : 0;
          return (
            <View key={i} style={styles.legendItem}>
              <View style={[styles.legendDot, { backgroundColor: seg.color || Colors.textMuted }]} />
              <Text style={styles.legendLabel} numberOfLines={1}>
                {seg.label}
              </Text>
              <Text style={styles.legendValue}>{seg.value.toLocaleString("ar-YE")}</Text>
              <Text style={styles.legendPct}>{pct}%</Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

/**
 * AdminDonutStat – A single stat card with mini bar indicator.
 */
export function AdminDonutStat({
  value,
  max,
  color,
  label,
  sublabel,
}: {
  value: number;
  max: number;
  color: string;
  label: string;
  sublabel?: string;
}) {
  const pct = max > 0 ? Math.max((value / max) * 100, 5) : 5;

  return (
    <View style={styles.miniCard}>
      <View style={styles.miniBarTrack}>
        <View style={[styles.miniBarFill, { flex: pct, backgroundColor: color }]} />
        <View style={[styles.miniBarRemainder, { flex: 100 - pct }]} />
      </View>
      <Text style={styles.miniValue}>{value.toLocaleString("ar-YE")}</Text>
      <Text style={styles.miniLabel}>{label}</Text>
      {sublabel ? <Text style={styles.miniSublabel}>{sublabel}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.md,
  },
  title: {
    color: Colors.text,
    ...Font.sectionTitle,
    textAlign: "right",
  },
  barRow: {
    flexDirection: "row-reverse",
    height: 16,
    borderRadius: 8,
    overflow: "hidden",
  },
  segment: {
    height: "100%",
  },
  totalRow: {
    flexDirection: "row-reverse",
    justifyContent: "center",
    alignItems: "center",
    gap: Spacing.sm,
  },
  totalLabel: {
    color: Colors.textSecondary,
    ...Font.caption,
  },
  totalValue: {
    color: Colors.text,
    fontSize: 22,
    fontWeight: "900",
    lineHeight: 28,
  },
  legend: {
    gap: Spacing.sm,
  },
  legendItem: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
    paddingVertical: Spacing.xs,
    paddingHorizontal: Spacing.sm,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm,
  },
  legendDot: {
    width: 10,
    height: 10,
    borderRadius: 5,
  },
  legendLabel: {
    flex: 1,
    color: Colors.text,
    ...Font.body,
    textAlign: "right",
  },
  legendValue: {
    color: Colors.text,
    ...Font.chip,
    minWidth: 50,
    textAlign: "left",
  },
  legendPct: {
    color: Colors.textSecondary,
    ...Font.small,
    width: 40,
    textAlign: "left",
  },
  miniCard: {
    alignItems: "center",
    gap: Spacing.xs,
    padding: Spacing.md,
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
  },
  miniBarTrack: {
    flexDirection: "row-reverse",
    width: "100%" as unknown as number,
    height: 6,
    borderRadius: 3,
    overflow: "hidden",
  },
  miniBarFill: {
    height: "100%",
    borderRadius: 3,
  },
  miniBarRemainder: {
    height: "100%",
    backgroundColor: Colors.surfaceAlt,
    borderRadius: 3,
  },
  miniValue: {
    color: Colors.text,
    fontSize: 18,
    fontWeight: "900",
    lineHeight: 24,
  },
  miniLabel: {
    color: Colors.textSecondary,
    ...Font.small,
    textAlign: "center",
  },
  miniSublabel: {
    color: Colors.textMuted,
    ...Font.tiny,
    textAlign: "center",
  },
});
