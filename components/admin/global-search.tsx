import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { useRef, useState } from "react";
import { Animated, StyleSheet, Text, TextInput, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Shadow, Spacing } from "./tokens";

type SearchResult = {
  id: string;
  label: string;
  subtitle?: string;
  icon?: string;
  route?: string;
};

/**
 * AdminGlobalSearch – Overlay search with instant results.
 */
export function AdminGlobalSearch({
  onResult,
}: {
  onResult: (item: SearchResult) => void;
}) {
  const [visible, setVisible] = useState(false);
  const [query, setQuery] = useState("");
  const opacity = useRef(new Animated.Value(0)).current;

  const open = () => {
    setVisible(true);
    Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }).start();
  };

  const close = () => {
    Animated.timing(opacity, { toValue: 0, duration: 150, useNativeDriver: true }).start(() => {
      setVisible(false);
      setQuery("");
    });
  };

  if (!visible) {
    return (
      <TouchableOpacity onPress={open} hitSlop={12} style={styles.trigger}>
        <MaterialIcons name="search" size={20} color={Colors.textMuted} />
      </TouchableOpacity>
    );
  }

  return (
    <Animated.View style={[styles.overlay, { opacity }]}>
      <View style={styles.searchBar}>
        <TouchableOpacity onPress={close} hitSlop={8}>
          <MaterialIcons name="arrow-forward" size={20} color={Colors.text} />
        </TouchableOpacity>
        <TextInput
          value={query}
          onChangeText={setQuery}
          placeholder="بحث سريع..."
          placeholderTextColor={Colors.textMuted}
          style={styles.input}
          textAlign="right"
          autoFocus
        />
        <MaterialIcons name="search" size={18} color={Colors.textMuted} />
      </View>
      {query.length > 1 && (
        <View style={styles.results}>
          <Text style={styles.noResults}>نتائج بحث &quot;{query}&quot;</Text>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  trigger: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    alignItems: "center",
    justifyContent: "center",
    backgroundColor: Colors.surfaceAlt,
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: Colors.bg,
    zIndex: 100,
    padding: Spacing.lg,
  },
  searchBar: {
    flexDirection: "row-reverse",
    alignItems: "center",
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    height: 50,
    paddingHorizontal: Spacing.lg,
    gap: Spacing.md,
    ...Shadow.raised,
  },
  input: {
    flex: 1,
    color: Colors.text,
    fontSize: 16,
    fontFamily: "Cairo",
    writingDirection: "rtl" as const,
  },
  results: {
    marginTop: Spacing.lg,
    backgroundColor: Colors.surface,
    borderRadius: Radius.md,
    padding: Spacing.xl,
  },
  noResults: {
    color: Colors.textMuted,
    ...Font.caption,
    textAlign: "center",
  },
});
