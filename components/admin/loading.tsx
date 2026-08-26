import { ActivityIndicator, View } from "react-native";
import { Colors, Spacing } from "./tokens";

/**
 * AdminLoading – Centered spinner for full-page loading.
 */
export function AdminLoading({ color }: { color?: string }) {
  return (
    <View
      style={{
        flex: 1,
        alignItems: "center",
        justifyContent: "center",
        paddingVertical: Spacing["4xl"],
      }}
    >
      <ActivityIndicator size="large" color={color ?? Colors.primary} />
    </View>
  );
}
