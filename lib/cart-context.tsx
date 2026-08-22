import AsyncStorage from "@react-native-async-storage/async-storage";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { ProductVariant, StoreProduct } from "@/lib/product-api";
import { djangoApi } from "@/lib/django-api";

export type CartItem = {
  lineId: string;
  product: StoreProduct;
  variantId?: number;
  color: string;
  size: string;
  unitPrice: number;
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
  validateCartWithServer: (cityId?: number, couponCode?: string, currency?: string) => Promise<any>;
};

const CartContext = createContext<CartContextValue | undefined>(undefined);
const STORAGE_KEY = "true-discount-fashion-cart-v2";

function findVariant(product: StoreProduct, color: string, size: string): ProductVariant | undefined {
  return product.variants.find((variant) => variant.isActive && variant.color === color && variant.size === size);
}

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
    const variant = findVariant(product, color, size);
    const variantId = variant?.id;
    const unitPrice = variant?.effectivePrice ?? product.price;
    const lineId = `${product.id}-${variantId ?? `${color}-${size}`}`;
    setItems((current) => {
      const existing = current.find((item) => item.lineId === lineId);
      if (!existing) return [...current, { lineId, product, variantId, color, size, unitPrice, quantity }];
      return current.map((item) => item.lineId === lineId ? { ...item, unitPrice, quantity: item.quantity + quantity } : item);
    });
  }, []);

  const updateQuantity = useCallback((lineId: string, quantity: number) => {
    setItems((current) => quantity <= 0 ? current.filter((item) => item.lineId !== lineId) : current.map((item) => item.lineId === lineId ? { ...item, quantity } : item));
  }, []);

  const removeItem = useCallback((lineId: string) => setItems((current) => current.filter((item) => item.lineId !== lineId)), []);
  const clearCart = useCallback(() => setItems([]), []);

  const validateCartWithServer = useCallback(async (cityId?: number, couponCode?: string, currency = "YER") => {
    const payload = {
      items: items.map((item) => ({ product_id: Number(item.product.id), variant_id: item.variantId, quantity: item.quantity })),
      city_id: cityId,
      coupon_code: couponCode,
      currency,
    };
    return djangoApi("/api/cart/calculate/", { method: "POST", body: JSON.stringify(payload) });
  }, [items]);

  const value = useMemo<CartContextValue>(() => ({
    validateCartWithServer,
    items,
    isReady,
    itemCount: items.reduce((total, item) => total + item.quantity, 0),
    subtotal: items.reduce((total, item) => total + item.unitPrice * item.quantity, 0),
    addItem,
    updateQuantity,
    removeItem,
    clearCart,
  }), [addItem, clearCart, isReady, items, removeItem, updateQuantity, validateCartWithServer]);

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart() {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart must be used inside CartProvider");
  return context;
}
