import { useEffect, useRef } from "react";
import { Animated, StyleSheet, View } from "react-native";
import { Colors, Radius, Spacing } from "./tokens";

/* ─── Skeleton Bar ────────────────────────────────── */

function SkeletonBar({ width, height, borderRadius }: { width?: number | `${number}%`; height?: number; borderRadius?: number }) {
  const opacity = useRef(new Animated.Value(0.4)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 1, duration: 800, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 0.4, duration: 800, useNativeDriver: true }),
      ])
    );
    loop.start();
    return () => loop.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Animated.View
      style={[
        styles.bar,
        {
          width: width ?? "100%",
          height: height ?? 14,
          borderRadius: borderRadius ?? Radius.sm,
          opacity,
        } as never,
      ]}
    />
  );
}

/* ─── Card Skeleton ───────────────────────────────── */

export function SkeletonCard({ rows = 3 }: { rows?: number }) {
  return (
    <View style={styles.card}>
      <View style={styles.cardRow}>
        <SkeletonBar width={44} height={44} borderRadius={Radius.sm} />
        <View style={styles.cardLines}>
          <SkeletonBar width="70%" height={14} />
          <SkeletonBar width="45%" height={10} />
        </View>
      </View>
      {Array.from({ length: rows }).map((_, i) => (
        <SkeletonBar key={i} width={i === rows - 1 ? "55%" : "100%"} height={10} />
      ))}
    </View>
  );
}

/* ─── List Skeleton ───────────────────────────────── */

export function SkeletonList({ count = 5, rows = 2 }: { count?: number; rows?: number }) {
  return (
    <View style={styles.list}>
      {Array.from({ length: count }).map((_, i) => (
        <SkeletonCard key={i} rows={rows} />
      ))}
    </View>
  );
}

/* ─── Table Row Skeleton ──────────────────────────── */

export function SkeletonTable({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <View style={styles.table}>
      {Array.from({ length: rows }).map((_, r) => (
        <View key={r} style={styles.tableRow}>
          {Array.from({ length: columns }).map((_, c) => (
            <SkeletonBar
              key={c}
              width={c === 0 ? "30%" : `${100 / columns / 1.5}%`}
              height={12}
            />
          ))}
        </View>
      ))}
    </View>
  );
}

/* ─── Stat Skeleton ───────────────────────────────── */

export function SkeletonStat({ count = 4 }: { count?: number }) {
  return (
    <View style={styles.statRow}>
      {Array.from({ length: count }).map((_, i) => (
        <View key={i} style={styles.statCard}>
          <SkeletonBar width={40} height={40} borderRadius={Radius.sm} />
          <SkeletonBar width="60%" height={10} />
          <SkeletonBar width="40%" height={20} />
        </View>
      ))}
    </View>
  );
}

/* ─── Page Skeleton ───────────────────────────────── */

export function SkeletonPage() {
  return (
    <View style={styles.page}>
      <View style={styles.pageHeader}>
        <SkeletonBar width={100} height={20} />
        <SkeletonBar width={60} height={14} />
      </View>
      <SkeletonStat count={3} />
      <SkeletonList count={4} rows={2} />
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: Colors.surfaceSunken,
  },
  card: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    marginBottom: Spacing.sm,
    gap: Spacing.md,
  },
  cardRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.md,
    marginBottom: Spacing.sm,
  },
  cardLines: {
    flex: 1,
    gap: Spacing.sm,
  },
  list: {
    gap: 0,
  },
  table: {
    gap: Spacing.md,
  },
  tableRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.lg,
    backgroundColor: Colors.surface,
    borderRadius: Radius.sm,
    padding: Spacing.md,
  },
  statRow: {
    flexDirection: "row-reverse",
    gap: Spacing.sm,
    marginBottom: Spacing.lg,
  },
  statCard: {
    flex: 1,
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.lg,
    gap: Spacing.sm,
  },
  page: {
    padding: Spacing.lg,
    gap: Spacing.lg,
  },
  pageHeader: {
    gap: Spacing.sm,
    alignItems: "flex-end",
  },
});
