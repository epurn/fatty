import { useEffect, useRef } from "react";
import { AccessibilityInfo, Animated, Pressable, StyleSheet, Text, View } from "react-native";

import type { DerivedItem } from "@/api/derivedItems";
import { ProvenanceIcon, Skeleton } from "@/components/ui";
import { useTheme, spacing, typeScale, radius } from "@/theme";

function formatKcal(n: number | null): string {
  if (n === null) return "—";
  return `${Math.round(n)} kcal`;
}

/**
 * Fades resolved item content in over the skeleton's footprint (FTY-180): a
 * short one-shot opacity transition from 0 to 1 on mount. Under Reduce Motion
 * the resolve is an instant swap — the value never animates in — mirroring
 * the `Skeleton` component's own motion opt-out.
 */
function useResolveFadeOpacity(): Animated.Value {
  // eslint-disable-next-line react-hooks/refs
  const opacity = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    let mounted = true;
    AccessibilityInfo.isReduceMotionEnabled().then(
      (reduced) => {
        if (!mounted) return;
        if (reduced) {
          opacity.setValue(1);
          return;
        }
        Animated.timing(opacity, {
          toValue: 1,
          duration: 220,
          useNativeDriver: true,
        }).start();
      },
      () => {
        if (mounted) opacity.setValue(1);
      },
    );
    return () => {
      mounted = false;
    };
  }, [opacity]);
  return opacity;
}

type ItemTimelineRowProps =
  | {
      /** True while the event is pending/processing — no resolved item yet. */
      loading: true;
      /** Screen-reader label conveying the in-progress status (e.g. "Estimating"). */
      accessibilityLabel: string;
    }
  | {
      loading?: false;
      item: DerivedItem;
      /** True when the parent log event is needs_clarification. */
      needsClarification?: boolean;
      onPress?: () => void;
    };

/**
 * A single derived item row in the Today timeline (FTY-098).
 *
 * Shows: name · kcal · always-on source icon (FTY-092 provenance).
 * "needs a detail" (needs_clarification parent) entries render muted with a
 * gentle inline tag and are visibly uncounted — they do not appear in hero
 * figures per the finalized-state filter, so no extra math needed here.
 * Tapping calls `onPress` (stub for FTY-100 detail sheet).
 *
 * `loading` drives the "thinking" state (FTY-180): a pending/processing entry
 * with no resolved item yet renders a `Skeleton` shimmer in the exact same
 * container geometry (row height, insets, icon slot, kcal column width) this
 * component uses once resolved, so the row never jumps or reflows when the
 * estimate lands — the values simply fade in over the placeholder's footprint.
 */
export function ItemTimelineRow(props: ItemTimelineRowProps) {
  const { colors } = useTheme();
  // Called unconditionally (rules-of-hooks): its value is only read once the
  // row resolves, but the loading branch returns early below.
  const opacity = useResolveFadeOpacity();

  if (props.loading) {
    return (
      <View
        style={[styles.row, { borderBottomColor: colors.separator }]}
        accessibilityRole="progressbar"
        accessibilityLabel={props.accessibilityLabel}
      >
        <View style={styles.iconSlot}>
          <Skeleton
            width={16}
            height={16}
            borderRadius={8}
            accessibilityElementsHidden
            importantForAccessibility="no-hide-descendants"
          />
        </View>
        <Skeleton
          width="55%"
          height={16}
          borderRadius={radius.sm}
          style={styles.nameSkeleton}
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
        />
        <Skeleton
          width={64}
          height={16}
          borderRadius={radius.sm}
          accessibilityElementsHidden
          importantForAccessibility="no-hide-descendants"
        />
      </View>
    );
  }

  const { item, needsClarification = false, onPress } = props;

  const name = item.name;
  const kcal =
    item.item_type === "food" ? item.calories : item.active_calories;
  const source = item.item_type === "food" ? item.source : null;
  const is_edited = item.is_edited ?? false;

  const textColor = needsClarification ? colors.textMuted : colors.text;
  const kcalColor = needsClarification ? colors.textMuted : colors.textSecondary;

  const a11yLabel = needsClarification
    ? `${name}, needs a detail, uncounted`
    : item.item_type === "food"
      ? `${name}, ${kcal !== null ? Math.round(kcal) : 0} kcal`
      : `${name}, ${kcal !== null ? Math.round(kcal) : 0} kcal burned`;

  return (
    <Animated.View style={{ opacity }}>
      <Pressable
        style={({ pressed }) => [
          styles.row,
          { borderBottomColor: colors.separator },
          pressed && { opacity: 0.7 },
        ]}
        onPress={onPress}
        accessibilityRole="button"
        accessibilityLabel={a11yLabel}
        accessibilityHint={needsClarification ? "Tap to add the missing detail" : "Tap to view details"}
      >
        {/* Provenance icon — always on */}
        <ProvenanceIcon source={source} is_edited={is_edited} />

        {/* Name */}
        <Text
          style={[styles.name, { color: textColor }]}
          numberOfLines={1}
          accessibilityElementsHidden
        >
          {name}
        </Text>

        {/* "needs a detail" tag */}
        {needsClarification ? (
          <View
            style={[styles.needsDetailTag, { backgroundColor: colors.controlBackground }]}
            accessibilityElementsHidden
          >
            <Text style={[styles.needsDetailText, { color: colors.textMuted }]}>
              needs a detail
            </Text>
          </View>
        ) : null}

        {/* Kcal — right-aligned */}
        <Text
          style={[styles.kcal, { color: kcalColor }]}
          accessibilityElementsHidden
        >
          {needsClarification ? "—" : formatKcal(kcal)}
        </Text>
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.sm,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.base,
    borderBottomWidth: StyleSheet.hairlineWidth,
    minHeight: 44,
  },
  name: {
    flex: 1,
    fontSize: typeScale.callout,
    fontWeight: "500",
  },
  // Matches ProvenanceIcon's own `icon` style width so the loading skeleton's
  // icon dot lands in the exact same slot the resolved provenance icon fills.
  iconSlot: {
    width: 22,
    alignItems: "center",
  },
  nameSkeleton: {
    flex: 1,
  },
  needsDetailTag: {
    borderRadius: radius.sm,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  needsDetailText: {
    fontSize: typeScale.caption2,
    fontWeight: "500",
  },
  kcal: {
    fontSize: typeScale.callout,
    fontVariant: ["tabular-nums"],
    minWidth: 64,
    textAlign: "right",
  },
});
