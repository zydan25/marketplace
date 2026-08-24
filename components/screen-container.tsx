import { View, type ViewProps } from "react-native";
import { SafeAreaView, type Edge } from "react-native-safe-area-context";

import { cn } from "@/lib/utils";

export interface ScreenContainerProps extends ViewProps {
  edges?: Edge[];
  className?: string;
  containerClassName?: string;
  safeAreaClassName?: string;
}

/**
 * Root page wrapper used by nearly every mobile route.
 * Keep the sizing contract explicit instead of relying only on NativeWind's
 * `flex-1`, because ScrollView/FlatList children require a bounded parent.
 */
export function ScreenContainer({
  children,
  edges = ["top", "left", "right"],
  className,
  containerClassName,
  safeAreaClassName,
  style,
  ...props
}: ScreenContainerProps) {
  return (
    <View
      className={cn("bg-background", containerClassName)}
      style={[{ flex: 1, minHeight: 0, width: "100%" }, style]}
      {...props}
    >
      <SafeAreaView
        edges={edges}
        className={cn("bg-background", safeAreaClassName)}
        style={{ flex: 1, minHeight: 0, width: "100%" }}
      >
        <View
          className={cn(className)}
          style={{ flex: 1, minHeight: 0, width: "100%" }}
        >
          {children}
        </View>
      </SafeAreaView>
    </View>
  );
}
