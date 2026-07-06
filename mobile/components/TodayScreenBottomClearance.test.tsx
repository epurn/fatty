import { StyleSheet } from "react-native";
import { act } from "react-test-renderer";

import { TodayScreen } from "./TodayScreen";
import { floatingSwitcherClearance } from "@/components/ui";
import { mockReduceMotion } from "@/testUtils/reduceMotion";

import {
  INACTIVE,
  SESSION,
  cleanupTrees,
  event,
  mount,
} from "./today/todayTestUtils";

jest.mock("@/theme/haptics", () => ({
  entryResolvedHaptic: jest.fn(),
  correctionSavedHaptic: jest.fn(),
  targetReachedHaptic: jest.fn(),
}));

jest.mock("expo-symbols", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactNative = require("react-native");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const ReactLib = require("react");
  return {
    SymbolView: ({ name }: { name: string }) =>
      ReactLib.createElement(ReactNative.View, {
        testID: `sf-symbol-${String(name)}`,
      }),
  };
});

jest.mock("expo-camera", () => ({
  useCameraPermissions: jest.fn(() => [
    { status: "granted", granted: true, canAskAgain: false, expires: "never" },
    jest.fn().mockResolvedValue({ status: "granted", granted: true }),
    jest.fn().mockResolvedValue({ status: "granted", granted: true }),
  ]),
  CameraView: jest.fn(() => null),
}));

jest.mock("expo-linking", () => ({
  openSettings: jest.fn().mockResolvedValue(undefined),
}));

jest.mock("@/api/logEvents", () => {
  const actual = jest.requireActual("@/api/logEvents");
  return {
    ...actual,
    listTodayLogEventEntries: jest.fn().mockResolvedValue([]),
  };
});

beforeEach(() => mockReduceMotion(false));

afterEach(cleanupTrees);

// FTY-242: the full-width bottom tab bar is retired in favour of the bottom-left
// floating switcher. Today reserves bottom clearance sourced from the switcher's
// own footprint so its last timeline row scrolls clear of the pill and the home
// indicator. The FTY-185 dimming scrim stays wired to Today (not dead code) and
// is retired alongside this clearance in FTY-257. These tests prove both the
// clearance reservation and that the scrim remains wired at the clearance height.
describe("TodayScreen bottom clearance (FTY-242 floating switcher)", () => {
  function mountToday() {
    const load = jest
      .fn()
      .mockResolvedValue([
        event({ id: "a", raw_text: "Oatmeal", status: "completed" }),
      ]);
    return mount(
      <TodayScreen session={SESSION} load={load} useActive={INACTIVE} />,
    );
  }

  it("reserves clearance for the floating switcher + home indicator", async () => {
    const tree = mountToday();
    await act(async () => {});

    const scroll = tree.root.find((n) => n.props.testID === "today-screen");
    const contentStyle = StyleSheet.flatten(
      scroll.props.contentContainerStyle,
    ) as { paddingBottom?: number };

    // The safe-area bottom inset seeded by the test SafeAreaProvider metrics
    // (see `mount` in todayTestUtils).
    const safeAreaBottom = 34;
    // The reserved clearance is the switcher's single source of truth — the
    // content must reserve exactly that so the last row clears the pill.
    expect(contentStyle.paddingBottom).toBe(
      floatingSwitcherClearance(safeAreaBottom),
    );
  });

  it("keeps the FTY-185 scrim wired at the clearance height (retired in FTY-257)", async () => {
    const tree = mountToday();
    await act(async () => {});

    const scrim = tree.root.find((n) => n.props.testID === "tab-bar-scrim");
    expect(scrim).toBeTruthy();

    const safeAreaBottom = 34;
    const style = StyleSheet.flatten(scrim.props.style) as { height?: number };
    // The scrim spans exactly the reserved clearance zone — same single source of
    // truth as the scroll padding, so the two can't drift.
    expect(style.height).toBe(floatingSwitcherClearance(safeAreaBottom));
  });
});
