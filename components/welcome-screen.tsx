import { useEffect, useRef } from "react";
import { Animated, StyleSheet, Text, View } from "react-native";

export function WelcomeScreen({ onFinished }: { onFinished: () => void }) {
  const opacity = useRef(new Animated.Value(0)).current;
  const scale = useRef(new Animated.Value(0.94)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(opacity, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.spring(scale, { toValue: 1, friction: 8, tension: 70, useNativeDriver: true }),
    ]).start();

    const exitTimer = setTimeout(() => {
      Animated.timing(opacity, { toValue: 0, duration: 450, useNativeDriver: true }).start(({ finished }) => {
        if (finished) onFinished();
      });
    }, 2200);

    return () => clearTimeout(exitTimer);
  }, [onFinished, opacity, scale]);

  return (
    <Animated.View style={[styles.root, { opacity }]} pointerEvents="auto">
      <Animated.View style={[styles.content, { transform: [{ scale }] }]}>
        <View style={styles.logoMark}>
          <Text style={styles.logoText}>ش</Text>
        </View>
        <Text style={styles.brand}>شبيك</Text>
        <Text style={styles.message}>شبيك لبيك... طلبك بين يديك</Text>
        <View style={styles.line} />
        <Text style={styles.sub}>تسوّق بسهولة، واختر ما يناسبك</Text>
      </Animated.View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    ...StyleSheet.absoluteFillObject,
    zIndex: 9999,
    elevation: 9999,
    backgroundColor: "#111111",
    alignItems: "center",
    justifyContent: "center",
  },
  content: { alignItems: "center", paddingHorizontal: 28 },
  logoMark: { width: 82, height: 82, borderRadius: 24, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", marginBottom: 18 },
  logoText: { fontSize: 42, fontWeight: "900", color: "#111111", fontFamily: "Cairo" },
  brand: { color: "#FFFFFF", fontSize: 30, fontWeight: "900", letterSpacing: 0.5, fontFamily: "Cairo" },
  message: { color: "#FFFFFF", fontSize: 18, fontWeight: "800", marginTop: 14, textAlign: "center", fontFamily: "Cairo" },
  line: { width: 54, height: 3, borderRadius: 3, backgroundColor: "#E60023", marginTop: 16 },
  sub: { color: "#AFAFAF", fontSize: 11, marginTop: 12, textAlign: "center", fontFamily: "Cairo" },
});
