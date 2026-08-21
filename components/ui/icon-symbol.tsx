import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { ComponentProps } from "react";
import { OpaqueColorValue, type StyleProp, type TextStyle } from "react-native";

const MAPPING = {
  "house.fill": "storefront",
  "square.grid.2x2.fill": "grid-view",
  "sparkles": "auto-awesome",
  "bag.fill": "shopping-bag",
  "person.fill": "person-outline",
  "chevron.right": "chevron-left",
  "chevron.left": "chevron-right",
  "magnifyingglass": "search",
  "bell.fill": "notifications-none",
  "heart": "favorite-border",
  "arrow.left": "arrow-back",
  "plus": "add",
  "minus": "remove",
  "xmark": "close",
  "gearshape.fill": "settings",
  "message.fill": "chat-bubble-outline",
  "tag.fill": "local-offer",
  "cube.box.fill": "inventory-2",
} as const satisfies Record<string, ComponentProps<typeof MaterialIcons>["name"]>;

export type IconSymbolName = keyof typeof MAPPING;

export function IconSymbol({ name, size = 24, color, style, weight: _weight }: { name: IconSymbolName; size?: number; color: string | OpaqueColorValue; style?: StyleProp<TextStyle>; weight?: string }) {
  return <MaterialIcons color={color} size={size} name={MAPPING[name]} style={style} />;
}
