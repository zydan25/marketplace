import { StyleSheet, Text, TouchableOpacity, View } from "react-native";
import MaterialIcons from "@expo/vector-icons/MaterialIcons";
import { router } from "expo-router";
import { ScreenContainer } from "@/components/screen-container";
import { useAuth } from "@/hooks/use-auth";
import { AdminPageHeader } from "./page-header";
import { AdminFooter } from "./footer";
import { ToastProvider } from "./toast";
import { Colors, Font, Radius, Spacing } from "./tokens";

/**
 * AdminLayout – Wraps every admin screen with:
 *  - Auth guard (redirects non-admin users)
 *  - Consistent SafeArea
 *  - Background color
 *  - Optional page header
 */
export function AdminLayout({
  children,
  title,
  subtitle,
  rightAction,
  headerless,
}: {
  children: React.ReactNode;
  title?: string;
  subtitle?: string;
  rightAction?: React.ReactNode;
  headerless?: boolean;
}) {
  const { user, isAuthenticated } = useAuth();

  if (!isAuthenticated || user?.role !== "admin") {
    return (
      <ScreenContainer
        edges={["top", "bottom", "left", "right"]}
        className="bg-white"
      >
        <View style={styles.denied}>
          <View style={styles.deniedIconWrap}>
            <MaterialIcons name="lock-outline" size={32} color={Colors.danger} />
          </View>
          <Text style={styles.deniedTitle}>هذه الصفحة للمدير فقط</Text>
          <Text style={styles.deniedText}>
            سجّلي الدخول بحساب الإدارة للوصول إلى لوحة التحكم.
          </Text>
          <TouchableOpacity
            style={styles.deniedButton}
            onPress={() => router.replace("/login" as never)}
          >
            <Text style={styles.deniedButtonText}>تسجيل الدخول</Text>
          </TouchableOpacity>
        </View>
      </ScreenContainer>
    );
  }

  return (
    <ScreenContainer
      edges={["top", "bottom", "left", "right"]}
      containerClassName="bg-background"
      className="bg-background"
    >
      {!headerless && title ? (
        <AdminPageHeader
          title={title}
          subtitle={subtitle}
          onBack={() => router.back()}
          rightAction={rightAction}
        />
      ) : null}
      <ToastProvider />
      <View style={styles.content}>{children}</View>
      <AdminFooter />
    </ScreenContainer>
  );
}

const styles = StyleSheet.create({
  content: {
    flex: 1,
    backgroundColor: Colors.bg,
  },
  denied: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: Spacing["3xl"],
    gap: Spacing.md,
  },
  deniedIconWrap: {
    width: 72,
    height: 72,
    borderRadius: Radius.xl,
    backgroundColor: Colors.dangerLight,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: Spacing.sm,
  },
  deniedTitle: {
    color: Colors.text,
    fontSize: 18,
    fontWeight: "900",
    textAlign: "center",
    fontFamily: "Cairo",
  },
  deniedText: {
    color: Colors.textSecondary,
    ...Font.caption,
    textAlign: "center",
    lineHeight: 20,
  },
  deniedButton: {
    backgroundColor: Colors.black,
    paddingHorizontal: Spacing.xl,
    paddingVertical: Spacing.md,
    borderRadius: Radius.sm,
    marginTop: Spacing.md,
  },
  deniedButtonText: {
    color: Colors.textInverse,
    ...Font.button,
  },
});
