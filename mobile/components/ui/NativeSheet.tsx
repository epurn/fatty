/**
 * NativeSheet — a controlled bottom sheet with genuine iOS detents.
 *
 * Wraps react-native-screens' declarative `ScreenStack` / `ScreenStackItem` to
 * present a real UIKit sheet: native detents (medium/large or fit-to-content),
 * the system grabber, swipe-to-dismiss, VoiceOver focus management, and the
 * content-dims-behind material — none of which a plain React Native `Modal`
 * can do (it fakes detents by switching a `maxHeight`).
 *
 * ## Why this mechanism (chosen for FTY-183)
 *
 * Expo SDK 57 (managed) ships `react-native-screens@4`, whose `ScreenStackItem`
 * exposes the UIKit sheet knobs directly (`sheetAllowedDetents`,
 * `sheetLargestUndimmedDetentIndex`, `sheetGrabberVisible`, `sheetCornerRadius`,
 * …). expo-router's own `formSheet` presentation is the same native machinery,
 * but it is *route*-based: a sheet route receives only serialisable params. Our
 * sheets (`CorrectionSheet`, `WeightLogSheet`) are controlled components that
 * hand their parent screen live callbacks (`onItemChange`, `onClarificationResolved`,
 * `onSaved`) and a full item object — data a route param cannot carry. So we
 * drive the same native primitive directly and keep the controlled component
 * API. No native module outside the managed SDK is added.
 *
 * Reduce Motion, the dimming material, and VoiceOver announcement all come from
 * the native presentation controller, so we do not reimplement them.
 *
 * The sheet mounts only while `visible`, presenting over the current screen; the
 * screen behind stays visible through any undimmed detent (see
 * `largestUndimmedDetentIndex`). A native swipe/tap-outside dismissal calls
 * `onClose` via `onDismissed`.
 */

import { useCallback, type ReactNode } from "react";
import {
  StyleSheet,
  View,
  type NativeSyntheticEvent,
  type StyleProp,
  type ViewStyle,
} from "react-native";
import { ScreenStack, ScreenStackItem } from "react-native-screens";

/** Detent stops, either explicit height fractions or a compact fit-to-content sheet. */
export type SheetDetents = number[] | "fitToContents";

export interface NativeSheetProps {
  /** Present the sheet when true; unmounts (native dismiss) when false. */
  visible: boolean;
  /** Called on any dismissal — native swipe/tap-outside or the caller's own action. */
  onClose: () => void;
  /**
   * Detents the sheet may rest at. `[0.5, 1]` = medium → large; `"fitToContents"`
   * = a true small sheet sized to its content.
   */
  detents: SheetDetents;
  /**
   * Index into `detents` of the largest detent for which the screen behind is
   * *not* dimmed (so it stays visible, e.g. the timeline behind the correction
   * sheet at medium). `"none"` dims at every detent; `"last"` never dims.
   */
  largestUndimmedDetentIndex?: number | "none" | "last";
  /** Detent the sheet opens at (index into `detents`). Defaults to the smallest. */
  initialDetentIndex?: number;
  /** Show the native drag grabber at the top. */
  grabberVisible?: boolean;
  /** Corner radius for the sheet; falls back to the system default when unset. */
  cornerRadius?: number;
  /** The sheet surface colour. */
  backgroundColor: string;
  /** VoiceOver label announcing the sheet on present. */
  accessibilityLabel?: string;
  /** Extra style for the sheet content container. */
  contentStyle?: StyleProp<ViewStyle>;
  children: ReactNode;
}

const BASE_SCREEN_ID = "native-sheet-presenter";
const SHEET_SCREEN_ID = "native-sheet-content";

export function NativeSheet({
  visible,
  onClose,
  detents,
  largestUndimmedDetentIndex = "none",
  initialDetentIndex = 0,
  grabberVisible = true,
  cornerRadius,
  backgroundColor,
  accessibilityLabel,
  contentStyle,
  children,
}: NativeSheetProps) {
  const handleDismissed = useCallback(
    (_e: NativeSyntheticEvent<{ dismissCount: number }>) => {
      onClose();
    },
    [onClose],
  );

  if (!visible) return null;

  return (
    // Full-window overlay; `box-none` so the transparent presenter never eats
    // touches meant for the screen behind an undimmed detent.
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <ScreenStack style={styles.stack}>
        {/*
          Transparent presenter screen. A native sheet is presented *over* a
          screen; this one is see-through so the app behind (e.g. the Today
          timeline) shows through the sheet's undimmed detent.
        */}
        <ScreenStackItem
          screenId={BASE_SCREEN_ID}
          stackPresentation="push"
          headerConfig={{ hidden: true }}
          style={styles.transparent}
          contentStyle={styles.transparent}
        />
        <ScreenStackItem
          screenId={SHEET_SCREEN_ID}
          stackPresentation="formSheet"
          headerConfig={{ hidden: true }}
          sheetAllowedDetents={detents}
          sheetInitialDetentIndex={initialDetentIndex}
          sheetLargestUndimmedDetentIndex={largestUndimmedDetentIndex}
          sheetGrabberVisible={grabberVisible}
          sheetCornerRadius={cornerRadius}
          nativeBackButtonDismissalEnabled
          onDismissed={handleDismissed}
          accessibilityViewIsModal
          accessibilityLabel={accessibilityLabel}
          style={[styles.sheet, { backgroundColor }]}
          contentStyle={[styles.sheet, { backgroundColor }, contentStyle]}
        >
          {children}
        </ScreenStackItem>
      </ScreenStack>
    </View>
  );
}

const styles = StyleSheet.create({
  stack: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "transparent",
  },
  transparent: {
    backgroundColor: "transparent",
  },
  sheet: {
    flex: 1,
  },
});
