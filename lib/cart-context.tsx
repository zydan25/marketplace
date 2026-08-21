import AsyncStorage from "@react-native-async-storage/async-storage";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { StoreProduct } from "@/lib/product-api";

export type CartItem = {
  lineId: string;
  product: StoreProduct;
  color: string;
  size: string;
  quantity: number;
};

type CartContextValue = {
  items: CartItem[];
  isReady: boolean;
  itemCount: number;
  subtotal: number;
  addItem: (product: StoreProduct, color: string, size: string, quantity?: number) => void;
  updateQuantity: (lineId: string, quantity: number) => void;
  removeItem: (lineId: string) => void;
  clearCart: () => void;
  validateCartWithServer?: (cityId?: number) => Promise<any>;
};

const CartContext = createContext<CartContextValue | undefined>(undefined);
const STORAGE_KEY = "true-discount-fashion-cart-v1";

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([]);
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    AsyncStorage.getItem(STORAGE_KEY)
      .then((saved) => {
        if (saved) setItems(JSON.parse(saved) as CartItem[]);
      })
      .catch(() => undefined)
      .finally(() => setIsReady(true));
  }, []);

  useEffect(() => {
    if (isReady) AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(items)).catch(() => undefined);
  }, [isReady, items]);

  const addItem = useCallback((product: StoreProduct, color: string, size: string, quantity = 1) => {
    const lineId = `${product.id}-${color}-${size}`;
    setItems((current) => {
      const existing = current.find((item) => item.lineId === lineId);
      if (!existing) return [...current, { lineId, product, color, size, quantity }];
      return current.map((item) => item.lineId === lineId ? { ...item, quantity: item.quantity + quantity } : item);
    });
  }, []);

  const updateQuantity = useCallback((lineId: string, quantity: number) => {
    setItems((current) => quantity <= 0 ? current.filter((item) => item.lineId !== lineId) : current.map((item) => item.lineId === lineId ? { ...item, quantity } : item));
  }, []);

  const removeItem = useCallback((lineId: string) => setItems((current) => current.filter((item) => item.lineId !== lineId)), []);
  const clearCart = useCallback(() => setItems([]), []);

  const validateCartWithServer = useCallback(async (cityId?: number) => {
    try {
      const { ApiClient } = require("./api-client");
      const payload = items.map(i => ({ product_id: i.product.id, quantity: i.quantity, color: i.color, size: i.size }));
      const result = await ApiClient.post("/api/cart/calculate/", { items: payload, city_id: cityId });
      return result;
    } catch (error) {
      console.warn("Cart validation failed", error);
      throw error;
    }
  }, [items]);

  const value = useMemo<CartContextValue & { validateCartWithServer: (cityId?: number) => Promise<any> }>(() => ({
    validateCartWithServer,
    items,
    isReady,
    itemCount: items.reduce((total, item) => total + item.quantity, 0),
    subtotal: items.reduce((total, item) => total + item.product.price * item.quantity, 0),
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
  }), [addItem, clearCart, isReady, items, removeItem, updateQuantity]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside CartProvider");
  return context;
}
