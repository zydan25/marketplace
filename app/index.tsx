import Constants from "expo-constants";
import { Redirect } from "expo-router";

export default function AppEntry() {
  const variant = Constants.expoConfig?.extra?.appVariant ?? process.env.APP_VARIANT ?? "customer";
  return <Redirect href={(variant === "vendor" ? "/vendor/login" : "/(tabs)") as never} />;
}
