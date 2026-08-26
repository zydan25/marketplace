import { useRef, useState } from "react";
import { Animated, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminCollapsible – Expandable/collapsible section with animation.
 */
export function AdminCollapsible({
  title,
  icon,
  defaultOpen = true,
  action,
  children,
}: {
  title: string;
  icon?: string;
  defaultOpen?: boolean;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const height = useRef(new Animated.Value(defaultOpen ? 1 : 0)).current;
  const rotation = useRef(new Animated.Value(defaultOpen ? 1 : 0)).current;

  const toggle = () => {
    const toValue = open ? 0 : 1;
    Animated.parallel([
      Animated.spring(height, { toValue, useNativeDriver: false }),
      Animated.spring(rotation, { toValue, useNativeDriver: true }),
    ]).start();
    setOpen(!open);
  };

  return (
    <View style={styles.container}>
      <TouchableOpacity style={styles.header} onPress={toggle} activeOpacity={0.7}>
        <View style={styles.headerRight}>
          {icon && (
            <View style={styles.iconWrap}>
              <MaterialIcons name={icon as never} size={18} color={Colors.primary} />
            </View>
          )}
          <Text style={styles.title}>{title}</Text>
        </View>
        <View style={styles.headerLeft}>
          {action}
          <Animated.View style={{ transform: [{ rotate: rotation.interpolate({ inputRange: [0, 1], outputRange: ["0deg", "180deg"] }) }] }}>
            <MaterialIcons name="expand-more" size={20} color={Colors.textMuted} />
          </Animated.View>
        </View>
      </TouchableOpacity>
      <Animated.View
        style={{
          maxHeight: height.interpolate({ inputRange: [0, 1], outputRange: [0, 2000] }),
          opacity: height,
          overflow: "hidden",
        }}
      >
        <View style={styles.content}>
          {children}
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    overflow: "hidden",
  },
  header: {
    flexDirection: "row-reverse",
    alignItems: "center",
    justifyContent: "space-between",
    padding: Spacing.lg,
  },
  headerRight: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
  },
  headerLeft: {
    flexDirection: "row-reverse",
    alignItems: "center",
    gap: Spacing.sm,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: Radius.sm,
    backgroundColor: Colors.primaryLight,
    alignItems: "center",
    justifyContent: "center",
  },
  title: {
    color: Colors.text,
    ...Font.sectionTitle,
  },
  content: {
    paddingHorizontal: Spacing.lg,
    paddingBottom: Spacing.lg,
  },
});
