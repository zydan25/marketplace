import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Shadow, Spacing } from "./tokens";

/**
 * AdminConfirmDialog – Inline confirmation dialog (replaces Alert.alert).
 */
export function AdminConfirmDialog({
  title,
  message,
  confirmLabel,
  cancelLabel,
  danger,
  onConfirm,
  onCancel,
}: {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  return (
    <View style={styles.overlay}>
      <View style={styles.dialog}>
        <Text style={styles.title}>{title}</Text>
        <Text style={styles.message}>{message}</Text>
        <View style={styles.actions}>
          <TouchableOpacity style={styles.cancelBtn} onPress={onCancel}>
            <Text style={styles.cancelText}>{cancelLabel ?? "إلغاء"}</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.confirmBtn, danger && styles.confirmDanger]}
            onPress={onConfirm}
          >
            <Text style={styles.confirmText}>
              {confirmLabel ?? "تأكيد"}
            </Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  overlay: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: "rgba(0,0,0,0.4)",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 999,
    padding: Spacing["3xl"],
  },
  dialog: {
    backgroundColor: Colors.surface,
    borderRadius: Radius.lg,
    padding: Spacing.xl,
    width: "100%",
    maxWidth: 360,
    ...Shadow.floating,
  },
  title: {
    color: Colors.text,
    ...Font.sectionTitle,
    textAlign: "center",
    marginBottom: Spacing.sm,
  },
  message: {
    color: Colors.textSecondary,
    ...Font.caption,
    textAlign: "center",
    lineHeight: 20,
    marginBottom: Spacing.xl,
  },
  actions: {
    flexDirection: "row",
    gap: Spacing.sm,
  },
  cancelBtn: {
    flex: 1,
    height: 44,
    borderRadius: Radius.sm,
    backgroundColor: Colors.surfaceAlt,
    borderWidth: 1,
    borderColor: Colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  cancelText: {
    color: Colors.textSecondary,
    ...Font.button,
  },
  confirmBtn: {
    flex: 1,
    height: 44,
    borderRadius: Radius.sm,
    backgroundColor: Colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  confirmDanger: {
    backgroundColor: Colors.danger,
  },
  confirmText: {
    color: Colors.textInverse,
    ...Font.button,
  },
});
