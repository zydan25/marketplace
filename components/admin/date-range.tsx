import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Colors, Font, Radius, Spacing } from "./tokens";

type Preset = "today" | "week" | "month" | "year" | "all";

const PRESETS: { key: Preset; label: string }[] = [
  { key: "today", label: "اليوم" },
  { key: "week", label: "الأسبوع" },
  { key: "month", label: "الشهر" },
  { key: "year", label: "السنة" },
  { key: "all", label: "الكل" },
];

function getPresetRange(preset: Preset): { from: string; to: string } {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const toStr = (d: Date) => d.toISOString().split("T")[0];

  switch (preset) {
    case "today":
      return { from: toStr(today), to: toStr(today) };
    case "week": {
      const start = new Date(today);
      start.setDate(start.getDate() - 6);
      return { from: toStr(start), to: toStr(today) };
    }
    case "month": {
      const start = new Date(today);
      start.setDate(start.getDate() - 29);
      return { from: toStr(start), to: toStr(today) };
    }
    case "year": {
      const start = new Date(today);
      start.setFullYear(start.getFullYear() - 1);
      return { from: toStr(start), to: toStr(today) };
    }
    case "all":
      return { from: "", to: "" };
  }
}

/**
 * AdminDateRange – Date range filter with preset buttons.
 */
export function AdminDateRange({
  preset,
  onPresetChange,
  from,
  to,
  onFromChange,
  onToChange,
}: {
  preset: Preset;
  onPresetChange: (p: Preset) => void;
  from?: string;
  to?: string;
  onFromChange?: (v: string) => void;
  onToChange?: (v: string) => void;
}) {
  return (
    <View style={styles.container}>
      <View style={styles.presets}>
        {PRESETS.map((p) => {
          const active = p.key === preset;
          return (
            <TouchableOpacity
              key={p.key}
              style={[styles.presetBtn, active && styles.presetBtnActive]}
              onPress={() => {
                onPresetChange(p.key);
                const range = getPresetRange(p.key);
                onFromChange?.(range.from);
                onToChange?.(range.to);
              }}
              activeOpacity={0.7}
            >
              <Text style={[styles.presetText, active && styles.presetTextActive]}>
                {p.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <View style={styles.customRow}>
        <View style={styles.dateInput}>
          <MaterialIcons name="calendar-today" size={14} color={Colors.textMuted} />
          <Text style={styles.dateText}>{from || "من تاريخ"}</Text>
        </View>
        <MaterialIcons name="arrow-back" size={14} color={Colors.textMuted} />
        <View style={styles.dateInput}>
          <MaterialIcons name="calendar-today" size={14} color={Colors.textMuted} />
          <Text style={styles.dateText}>{to || "إلى تاريخ"}</Text>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    gap: Spacing.sm,
  },
  presets: {
    flexDirection: "row-reverse",
    gap: Spacing.xs,
    flexWrap: "wrap",
  },
  presetBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    borderRadius: Radius.sm,
    backgroundColor: Colors.surfaceAlt,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  presetBtnActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  presetText: {
    color: Colors.textSecondary,
    ...Font.chip,
  },
  presetTextActive: {
    color: Colors.textInverse,
    fontWeight: "700",
  },
  customRow: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
  },
  dateInput: {
    flex: 1,
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.xs,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    backgroundColor: Colors.surface,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  dateText: {
    color: Colors.textMuted,
    ...Font.small,
  },
});
