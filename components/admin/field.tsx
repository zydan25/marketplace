import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminField – Labeled form field with helper and error.
 */
export function AdminField({
  label,
  helper,
  error,
  compact,
  ...props
}: {
  label: string;
  helper?: string;
  error?: string;
  compact?: boolean;
} & TextInputProps) {
  return (
    <View style={[styles.wrap, compact && styles.wrapCompact]}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        {...props}
        style={[styles.input, error && styles.inputError, props.style]}
        placeholderTextColor={Colors.textMuted}
        textAlign="right"
      />
      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : helper ? (
        <Text style={styles.helper}>{helper}</Text>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    marginBottom: Spacing.lg,
  },
  wrapCompact: {
    flex: 1,
  },
  label: {
    color: Colors.text,
    ...Font.label,
    textAlign: "right",
    marginBottom: Spacing.sm,
  },
  input: {
    height: 48,
    backgroundColor: Colors.surfaceAlt,
    borderRadius: Radius.sm,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: Spacing.md,
    color: Colors.text,
    fontSize: 14,
    fontFamily: "Cairo",
    writingDirection: "rtl" as const,
  },
  inputError: {
    borderColor: Colors.danger,
  },
  helper: {
    color: Colors.textMuted,
    ...Font.tiny,
    textAlign: "right",
    marginTop: Spacing.xs,
  },
  error: {
    color: Colors.danger,
    ...Font.tiny,
    textAlign: "right",
    marginTop: Spacing.xs,
  },
});
