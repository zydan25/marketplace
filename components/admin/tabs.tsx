import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminTabs – Horizontal scrollable tab bar with animated indicator.
 */
export function AdminTabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: T; label: string; icon?: string }[];
  active: T;
  onChange: (key: T) => void;
}) {
  return (
    <View style={styles.container}>
      {tabs.map((tab) => {
        const isActive = tab.key === active;
        return (
          <TouchableOpacity
            key={tab.key}
            style={[styles.tab, isActive && styles.tabActive]}
            onPress={() => onChange(tab.key)}
            activeOpacity={0.7}
          >
            <Text style={[styles.label, isActive && styles.labelActive]}>
              {tab.label}
            </Text>
            {isActive && <View style={styles.indicator} />}
          </TouchableOpacity>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row-reverse",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.xs,
    gap: Spacing.xs,
  },
  tab: {
    flex: 1,
    paddingVertical: Spacing.md,
    alignItems: "center",
    justifyContent: "center",
    borderRadius: Radius.sm,
    position: "relative",
  },
  tabActive: {
    backgroundColor: Colors.primary,
  },
  label: {
    color: Colors.textSecondary,
    ...Font.chip,
  },
  labelActive: {
    color: Colors.textInverse,
    fontWeight: "700",
  },
  indicator: {
    position: "absolute",
    bottom: 4,
    width: 20,
    height: 3,
    borderRadius: 2,
    backgroundColor: "rgba(255,255,255,0.6)",
  },
});
