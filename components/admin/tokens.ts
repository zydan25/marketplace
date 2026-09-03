/**
 * Admin Design System – Central Tokens
 *
 * Premium Arabic E-commerce Admin Dashboard
 * Symmetrical · Soft Neumorphism · Modern Minimal · RTL Arabic-first
 */

import { StyleSheet } from "react-native";

export const Colors = {
  bg: "#F2F2F7", surface: "#FFFFFF", surfaceAlt: "#F8F8FA", surfaceSunken: "#EDEDF0",
  primary: "#E60023", primaryLight: "#FFF0F3", primaryDark: "#C4001E",
  success: "#168451", successLight: "#ECF8F1", warning: "#E97B11", warningLight: "#FFF5E8",
  danger: "#E60023", dangerLight: "#FFF0F3", info: "#007AFF", infoLight: "#E8F4FF",
  text: "#1C1C1E", textSecondary: "#6C6C70", textMuted: "#AEAEB2", textInverse: "#FFFFFF",
  border: "#E5E5EA", divider: "#F2F2F7", black: "#1C1C1E", white: "#FFFFFF",
} as const;

export const Spacing = { xs:4, sm:8, md:12, lg:16, xl:20, "2xl":24, "3xl":32, "4xl":40 } as const;
export const Radius = { sm:8, md:12, lg:16, xl:20, "2xl":24, full:9999 } as const;
const CAIRO = "Cairo";
export const Font = {
  pageTitle:{fontSize:22,fontWeight:"900" as const,lineHeight:30,fontFamily:CAIRO},
  sectionTitle:{fontSize:17,fontWeight:"800" as const,lineHeight:24,fontFamily:CAIRO},
  cardTitle:{fontSize:14,fontWeight:"800" as const,lineHeight:20,fontFamily:CAIRO},
  body:{fontSize:14,fontWeight:"500" as const,lineHeight:21,fontFamily:CAIRO},
  caption:{fontSize:12,fontWeight:"500" as const,lineHeight:17,fontFamily:CAIRO},
  label:{fontSize:13,fontWeight:"700" as const,lineHeight:18,fontFamily:CAIRO},
  small:{fontSize:11,fontWeight:"500" as const,lineHeight:16,fontFamily:CAIRO},
  tiny:{fontSize:10,fontWeight:"500" as const,lineHeight:14,fontFamily:CAIRO},
  button:{fontSize:15,fontWeight:"700" as const,lineHeight:20,fontFamily:CAIRO},
  chip:{fontSize:13,fontWeight:"600" as const,lineHeight:18,fontFamily:CAIRO},
} as const;

export const Shadow = {
  soft:{shadowColor:"#000",shadowOffset:{width:0,height:1},shadowOpacity:0.04,shadowRadius:3,elevation:1},
  raised:{shadowColor:"#000",shadowOffset:{width:0,height:2},shadowOpacity:0.06,shadowRadius:8,elevation:3},
  floating:{shadowColor:"#000",shadowOffset:{width:0,height:4},shadowOpacity:0.10,shadowRadius:16,elevation:8},
  pressed:{shadowColor:"#000",shadowOffset:{width:0,height:-1},shadowOpacity:0.05,shadowRadius:2,elevation:0},
  md:{shadowColor:"#000",shadowOffset:{width:0,height:2},shadowOpacity:0.06,shadowRadius:8,elevation:3},
  sm:{shadowColor:"#000",shadowOffset:{width:0,height:1},shadowOpacity:0.04,shadowRadius:3,elevation:1},
} as const;

export const AdminStyles = StyleSheet.create({
  screen:{flex:1,backgroundColor:Colors.bg},
  header:{height:56,backgroundColor:Colors.surface,paddingHorizontal:Spacing.lg,flexDirection:"row",alignItems:"center",justifyContent:"space-between",borderBottomWidth:StyleSheet.hairlineWidth,borderBottomColor:Colors.border},
  headerTitle:{color:Colors.text,fontSize:17,fontWeight:"800",fontFamily:CAIRO}, headerSpacer:{width:32},
  card:{backgroundColor:Colors.surface,borderRadius:Radius.md,padding:Spacing.lg,...Shadow.soft}, cardFlat:{backgroundColor:Colors.surface,borderRadius:Radius.md,padding:Spacing.lg},
  input:{height:48,backgroundColor:Colors.surfaceAlt,borderRadius:Radius.sm,borderWidth:1,borderColor:Colors.border,paddingHorizontal:Spacing.md,color:Colors.text,fontSize:14,fontFamily:CAIRO,writingDirection:"rtl" as const},
  btnPrimary:{height:48,backgroundColor:Colors.primary,borderRadius:Radius.sm,alignItems:"center" as const,justifyContent:"center" as const},
  btnSecondary:{height:48,backgroundColor:Colors.surfaceAlt,borderRadius:Radius.sm,borderWidth:1,borderColor:Colors.border,alignItems:"center" as const,justifyContent:"center" as const},
  btnSuccess:{height:48,backgroundColor:Colors.success,borderRadius:Radius.sm,alignItems:"center" as const,justifyContent:"center" as const},
  btnTextWhite:{color:Colors.textInverse,fontSize:15,fontWeight:"700",fontFamily:CAIRO},
  chip:{paddingHorizontal:Spacing.md,paddingVertical:Spacing.sm,borderRadius:Radius.sm,borderWidth:1,borderColor:Colors.border,backgroundColor:Colors.surface},
  chipActive:{backgroundColor:Colors.black,borderColor:Colors.black},
  search:{backgroundColor:Colors.surface,borderRadius:Radius.sm,height:46,flexDirection:"row" as const,alignItems:"center" as const,paddingHorizontal:Spacing.md,gap:Spacing.sm,borderWidth:1,borderColor:Colors.border},
  section:{backgroundColor:Colors.surface,borderRadius:Radius.md,padding:Spacing.lg,...Shadow.soft},
  listItem:{backgroundColor:Colors.surface,borderRadius:Radius.md,padding:Spacing.md,marginBottom:Spacing.sm,flexDirection:"row" as const,alignItems:"center" as const,gap:Spacing.md,...Shadow.soft},
  badge:{paddingHorizontal:Spacing.sm,paddingVertical:3,borderRadius:Radius.full,alignSelf:"flex-start" as const},
  emptyContainer:{alignItems:"center" as const,justifyContent:"center" as const,paddingVertical:Spacing["4xl"],gap:Spacing.sm},
  deniedContainer:{flex:1,alignItems:"center" as const,justifyContent:"center" as const,padding:Spacing["3xl"],gap:Spacing.md},
  row:{flexDirection:"row" as const,gap:Spacing.md},
});
