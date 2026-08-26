import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminPagination – RTL page navigation controls.
 */
export function AdminPagination({
  currentPage,
  totalPages,
  onPageChange,
}: {
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const pages: (number | "...")[] = [];
  if (totalPages <= 5) {
    for (let i = 1; i <= totalPages; i++) pages.push(i);
  } else {
    pages.push(1);
    if (currentPage > 3) pages.push("...");
    for (let i = Math.max(2, currentPage - 1); i <= Math.min(totalPages - 1, currentPage + 1); i++) {
      pages.push(i);
    }
    if (currentPage < totalPages - 2) pages.push("...");
    pages.push(totalPages);
  }

  return (
    <View style={styles.container}>
      <TouchableOpacity
        style={[styles.navBtn, currentPage <= 1 && styles.navBtnDisabled]}
        disabled={currentPage <= 1}
        onPress={() => onPageChange(currentPage - 1)}
      >
        <MaterialIcons name="chevron-right" size={18} color={currentPage <= 1 ? Colors.textMuted : Colors.text} />
      </TouchableOpacity>

      {pages.map((page, index) =>
        page === "..." ? (
          <Text key={`dots-${index}`} style={styles.dots}>…</Text>
        ) : (
          <TouchableOpacity
            key={page}
            style={[styles.pageBtn, page === currentPage && styles.pageBtnActive]}
            onPress={() => onPageChange(page)}
          >
            <Text style={[styles.pageText, page === currentPage && styles.pageTextActive]}>
              {page}
            </Text>
          </TouchableOpacity>
        )
      )}

      <TouchableOpacity
        style={[styles.navBtn, currentPage >= totalPages && styles.navBtnDisabled]}
        disabled={currentPage >= totalPages}
        onPress={() => onPageChange(currentPage + 1)}
      >
        <MaterialIcons name="chevron-left" size={18} color={currentPage >= totalPages ? Colors.textMuted : Colors.text} />
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flexDirection: "row-reverse",
    alignItems: "center",
    justifyContent: "center",
    gap: Spacing.xs,
    paddingVertical: Spacing.lg,
  },
  navBtn: {
    width: 36,
    height: 36,
    borderRadius: Radius.sm,
    backgroundColor: Colors.surface,
    alignItems: "center",
    justifyContent: "center",
    borderWidth: 1,
    borderColor: Colors.border,
  },
  navBtnDisabled: {
    opacity: 0.4,
  },
  pageBtn: {
    minWidth: 36,
    height: 36,
    borderRadius: Radius.sm,
    backgroundColor: Colors.surface,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: Spacing.sm,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  pageBtnActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  pageText: {
    color: Colors.text,
    ...Font.chip,
  },
  pageTextActive: {
    color: Colors.textInverse,
    fontWeight: "700",
  },
  dots: {
    color: Colors.textMuted,
    ...Font.chip,
    paddingHorizontal: 4,
  },
});
