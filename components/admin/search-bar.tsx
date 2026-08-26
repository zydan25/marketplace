import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, TextInput, View } from "react-native";
import { Colors, Radius, Spacing } from "./tokens";

/**
 * AdminSearchBar – RTL search input with icon.
 */
export function AdminSearchBar({
  value,
  onChangeText,
  placeholder,
}: {
  value: string;
  onChangeText: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <View style={styles.bar}>
      <TextInput
        value={value}
        onChangeText={onChangeText}
        placeholder={placeholder ?? "بحث..."}
        placeholderTextColor={Colors.textMuted}
        style={styles.input}
        textAlign="right"
      />
      <MaterialIcons name="search" size={18} color={Colors.textMuted} />
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.sm,
    height: 44,
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: Spacing.md,
    gap: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  input: {
    flex: 1,
    color: Colors.text,
    fontSize: 14,
    writingDirection: "rtl" as const,
  },
});
