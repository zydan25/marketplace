import Constants from "expo-constants";
import { Redirect } from "expo-router";
import { useState } from "react";

import { WelcomeScreen } from "@/components/welcome-screen";

export default function AppEntry() {
  const [showWelcome, setShowWelcome] = useState(true);
  const variant = Constants.expoConfig?.extra?.appVariant ?? process.env.APP_VARIANT ?? "customer";

  if (showWelcome) {
    return <WelcomeScreen onFinished={() => setShowWelcome(false)} />;
  }

  return <Redirect href={(variant === "vendor" ? "/vendor/login" : "/(tabs)") as never} />;
}
