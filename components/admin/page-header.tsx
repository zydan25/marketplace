import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { useThemeContext } from "@/lib/theme-provider";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminPageHeader – Unified page header for all admin screens.
 * RTL-first, symmetrical, neumorphic.
 */
export function AdminPageHeader({
  title,
  subtitle,
  onBack,
  rightAction,
}: {
  title: string;
  subtitle?: string;
  onBack?: () => void;
  rightAction?: React.ReactNode;
}) {
  return (
    <View style={styles.header}>
      <View style={styles.left}>
        {rightAction ?? <View style={styles.spacer} />}
      </View>
      <View style={styles.center}>
        <Text style={styles.title} numberOfLines={1}>
          {title}
        </Text>
        {subtitle ? (
          <Text style={styles.subtitle} numberOfLines={1}>
            {subtitle}
          </Text>
        ) : null}
      </View>
      <View style={styles.right}>
        {onBack ? (
          <TouchableOpacity
            onPress={onBack}
            hitSlop={12}
            style={styles.backBtn}
          >
            <MaterialIcons name="arrow-forward" size={22} color={Colors.text} />
          </TouchableOpacity>
        ) : (
          <View style={styles.spacer} />
        )}
      </View>
    </View>
  );
}

/**
 * AdminPageHeaderAction – A small icon-button for the right side.
 */
export function AdminPageHeaderAction({
  icon,
  onPress,
  color,
}: {
  icon: string;
  onPress: () => void;
  color?: string;
}) {
  return (
    <TouchableOpacity onPress={onPress} hitSlop={12} style={styles.backBtn}>
      <MaterialIcons
        name={icon as never}
        size={22}
        color={color ?? Colors.primary}
      />
    </TouchableOpacity>
  );
}

/**
 * AdminDarkModeToggle – Toggle between light/dark mode.
 */
export function AdminDarkModeToggle() {
  const { colorScheme, setColorScheme } = useThemeContext();
  const isDark = colorScheme === "dark";

  return (
    <TouchableOpacity
      onPress={() => setColorScheme(isDark ? "light" : "dark")}
      hitSlop={12}
      style={styles.backBtn}
    >
      <MaterialIcons
        name={isDark ? "light-mode" : "dark-mode"}
        size={20}
        color={Colors.text}
      />
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  header: {
    height: 56,
    backgroundColor: Colors.surface,
    paddingHorizontal: Spacing.lg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: Colors.border,
  },
  left: { width: 56, alignItems: "flex-end" },
  center: { flex: 1, alignItems: "center" },
  right: { width: 56, alignItems: "flex-start" },
  spacer: { width: 32 },
  backBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.surfaceAlt,
  },
  title: {
    color: Colors.text,
    ...Font.sectionTitle,
  },
  subtitle: {
    color: Colors.textSecondary,
    ...Font.tiny,
    marginTop: 2,
  },
});
