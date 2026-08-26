import { ScrollView, StyleSheet, Text, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

type Column<T> = {
  key: string;
  label: string;
  width?: number;
  render?: (item: T) => React.ReactNode;
  align?: "left" | "right" | "center";
};

/**
 * AdminDataTable – Scrollable data table with RTL support.
 */
export function AdminDataTable<T extends Record<string, any>>({
  columns,
  data,
  emptyMessage,
  keyExtractor,
}: {
  columns: Column<T>[];
  data: T[];
  emptyMessage?: string;
  keyExtractor: (item: T, index: number) => string;
}) {
  if (data.length === 0) {
    return (
      <View style={styles.empty}>
        <Text style={styles.emptyText}>{emptyMessage || "لا توجد بيانات"}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <View style={{ minWidth: "100%" }}>
          {/* Header */}
          <View style={styles.headerRow}>
            {columns.map((col) => (
              <View
                key={col.key}
                style={[styles.headerCell, { width: col.width ?? 100 }]}
              >
                <Text style={styles.headerText}>{col.label}</Text>
              </View>
            ))}
          </View>

          {/* Rows */}
          {data.map((item, rowIndex) => (
            <View
              key={keyExtractor(item, rowIndex)}
              style={[styles.row, rowIndex % 2 === 1 && styles.rowAlt]}
            >
              {columns.map((col) => (
                <View
                  key={col.key}
                  style={[styles.cell, { width: col.width ?? 100 }]}
                >
                  {col.render ? (
                    col.render(item)
                  ) : (
                    <Text style={styles.cellText} numberOfLines={1}>
                      {String(item[col.key] ?? "-")}
                    </Text>
                  )}
                </View>
              ))}
            </View>
          ))}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    overflow: "hidden",
  },
  headerRow: {
    flexDirection: "row-reverse",
    backgroundColor: Colors.surfaceAlt,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  headerCell: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
  },
  headerText: {
    color: Colors.textSecondary,
    ...Font.label,
    textAlign: "right",
  },
  row: {
    flexDirection: "row-reverse",
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.divider,
    minHeight: 48,
    alignItems: "center",
  },
  rowAlt: {
    backgroundColor: Colors.surfaceAlt,
  },
  cell: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
  },
  cellText: {
    color: Colors.text,
    ...Font.body,
    textAlign: "right",
  },
  empty: {
    paddingVertical: Spacing["3xl"],
    alignItems: "center",
  },
  emptyText: {
    color: Colors.textMuted,
    ...Font.caption,
  },
});
