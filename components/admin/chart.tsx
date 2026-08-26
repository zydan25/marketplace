import { StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

type BarData = {
  label: string;
  value: number;
  color?: string;
};

/**
 * AdminBarChart – Simple horizontal bar chart.
 * No external dependencies – pure React Native Views.
 */
export function AdminBarChart({
  data,
  title,
  maxValue,
  formatValue,
}: {
  data: BarData[];
  title?: string;
  maxValue?: number;
  formatValue?: (value: number) => string;
}) {
  const max = maxValue ?? Math.max(...data.map((d) => d.value), 1);

  return (
    <View style={styles.container}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      <View style={styles.chart}>
        {data.map((item, index) => {
          const pct = Math.min((item.value / max) * 100, 100);
          return (
            <View key={index} style={styles.row}>
              <Text style={styles.label} numberOfLines={1}>{item.label}</Text>
              <View style={styles.barWrap}>
                <View
                  style={[
                    styles.bar,
                    {
                      width: `${Math.max(pct, 2)}%`,
                      backgroundColor: item.color ?? Colors.primary,
                    },
                  ]}
                />
              </View>
              <Text style={styles.value}>
                {formatValue ? formatValue(item.value) : item.value}
              </Text>
            </View>
          );
        })}
      </View>
    </View>
  );
}

/**
 * AdminStatChart – Mini stat with a small inline bar (sparkline-style).
 */
export function AdminMiniBar({
  value,
  maxValue,
  color,
  label,
}: {
  value: number;
  maxValue: number;
  color?: string;
  label?: string;
}) {
  const pct = maxValue > 0 ? Math.min((value / maxValue) * 100, 100) : 0;

  return (
    <View style={styles.miniWrap}>
      {label ? <Text style={styles.miniLabel}>{label}</Text> : null}
      <View style={styles.miniTrack}>
        <View
          style={[
            styles.miniFill,
            { width: `${Math.max(pct, 2)}%`, backgroundColor: color ?? Colors.primary },
          ]}
        />
      </View>
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
  chart: {
    gap: Spacing.md,
  },
  row: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
  },
  label: {
    color: Colors.textSecondary,
    ...Font.small,
    width: 70,
    textAlign: "right",
  },
  barWrap: {
    flex: 1,
    height: 20,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm,
    overflow: "hidden",
  },
  bar: {
    height: "100%",
    borderRadius: Radius.sm,
  },
  value: {
    color: Colors.text,
    ...Font.chip,
    width: 60,
    textAlign: "left",
  },
  miniWrap: {
    gap: Spacing.xs,
  },
  miniLabel: {
    color: Colors.textSecondary,
    ...Font.tiny,
    textAlign: "right",
  },
  miniTrack: {
    height: 6,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: 3,
    overflow: "hidden",
  },
  miniFill: {
    height: "100%",
    borderRadius: 3,
  },
});
