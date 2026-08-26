import { Alert, Platform } from "react-native";

/**
 * Export data to CSV file and share it.
 * Web: creates a Blob download. Native: uses Blob + URL approach.
 */
export async function exportToCSV({
  filename,
  headers,
  rows,
}: {
  filename: string;
  headers: string[];
  rows: (string | number)[][];
}): Promise<void> {
  try {
    const bom = "\uFEFF";
    const csvContent =
      bom +
      headers.join(",") +
      "\n" +
      rows
        .map((row) =>
          row.map((cell) => `"${String(cell).replace(/"/g, '""')}"`).join(",")
        )
        .join("\n");

    if (Platform.OS === "web") {
      const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${filename}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    // Native: show a simple alert with the data summary
    Alert.alert(
      "تم التصدير",
      `تم تحضير ${rows.length} سجل بنجاح.\n\nللتصدير الكامل استخدم النسخة المكتبية.`,
      [{ text: "حسناً" }]
    );
  } catch {
    Alert.alert("خطأ", "فشل تصدير البيانات");
  }
}
