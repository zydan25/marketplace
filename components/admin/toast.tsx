import { useEffect, useRef, useState } from "react";
import { Animated, StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Shadow, Spacing } from "./tokens";

export type ToastType = "success" | "error" | "warning" | "info";

type ToastMessage = {
  id: string;
  text: string;
  type: ToastType;
};

let _listeners: ((msg: ToastMessage) => void)[] = [];

/**
 * Show a toast from anywhere (no context needed).
 *
 *   showToast("تم الحفظ بنجاح", "success");
 *   showToast("حدث خطأ", "error");
 */
export function showToast(text: string, type: ToastType = "info") {
  const msg: ToastMessage = { id: `${Date.now()}-${Math.random()}`, text, type };
  _listeners.forEach((fn) => fn(msg));
}

/* ─── Provider (mount once in AdminLayout) ──────── */

const TOAST_CONFIG: Record<ToastType, { bg: string; icon: string; color: string }> = {
  success: { bg: Colors.success, icon: "✓", color: Colors.textInverse },
  error: { bg: Colors.danger, icon: "✕", color: Colors.textInverse },
  warning: { bg: Colors.warning, icon: "!", color: Colors.textInverse },
  info: { bg: Colors.info, icon: "i", color: Colors.textInverse },
};

const DURATION = 3000;

export function ToastProvider() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    const listener = (msg: ToastMessage) => {
      setToasts((prev) => [...prev.slice(-2), msg]);
    };
    _listeners.push(listener);
    return () => { _listeners = _listeners.filter((fn) => fn !== listener); };
  }, []);

  useEffect(() => {
    if (toasts.length === 0) return;
    const timer = setTimeout(() => {
      setToasts((prev) => prev.slice(1));
    }, DURATION);
    return () => clearTimeout(timer);
  }, [toasts]);

  return (
    <View style={styles.container} pointerEvents="box-none">
      {toasts.map((t) => (
        <ToastItem
          key={t.id}
          message={t}
          onDismiss={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
        />
      ))}
    </View>
  );
}

function ToastItem({ message, onDismiss }: { message: ToastMessage; onDismiss: () => void }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(-20)).current;
  const cfg = TOAST_CONFIG[message.type];

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 250, useNativeDriver: true }),
      Animated.timing(translateY, { toValue: 0, duration: 250, useNativeDriver: true }),
    ]).start();
    const timer = setTimeout(() => {
      Animated.parallel([
        Animated.timing(opacity, { toValue: 0, duration: 200, useNativeDriver: true }),
        Animated.timing(translateY, { toValue: -20, duration: 200, useNativeDriver: true }),
      ]).start(() => onDismiss());
    }, DURATION - 200);
    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Animated.View style={[styles.toast, { backgroundColor: cfg.bg, opacity, transform: [{ translateY }] }]}>
      <View style={[styles.iconCircle, { backgroundColor: "rgba(255,255,255,0.2)" }]}>
        <Text style={[styles.iconText, { color: cfg.color }]}>{cfg.icon}</Text>
      </View>
      <Text style={[styles.text, { color: cfg.color }]} numberOfLines={2}>
        {message.text}
      </Text>
      <TouchableOpacity onPress={onDismiss} hitSlop={8}>
        <Text style={[styles.dismiss, { color: cfg.color }]}>✕</Text>
      </TouchableOpacity>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: "absolute",
    top: 60,
    left: Spacing.lg,
    right: Spacing.lg,
    zIndex: 9999,
    gap: Spacing.sm,
  },
  toast: {
    flexDirection: "row",
    alignItems: "center",
    gap: Spacing.sm,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
    borderRadius: Radius.md,
    ...Shadow.floating,
  },
  iconCircle: {
    width: 28,
    height: 28,
    borderRadius: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  iconText: {
    fontSize: 14,
    fontWeight: "800",
    fontFamily: "Cairo",
  },
  text: {
    flex: 1,
    ...Font.body,
    fontWeight: "600",
  },
  dismiss: {
    fontSize: 14,
    fontWeight: "700",
    fontFamily: "Cairo",
    padding: 4,
  },
});
