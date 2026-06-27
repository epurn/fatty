/**
 * Presentation + edit logic for derived food/exercise items (FTY-050).
 *
 * The wire model — the `DerivedItem` DTOs and the edit client — lives in
 * `@/api/derivedItems`. This module is the pure, testable core of the editable
 * item surface: the per-type editable field vocabulary, reading a field's
 * current vs estimated value, deciding whether a field was corrected (the
 * edited-vs-estimated indicator), compact value formatting, and the optimistic
 * single-field apply used before the server response lands.
 *
 * It deliberately holds **no** rescale math: a servings/quantity edit rescales
 * calories/macros server-side (per FTY-051), and the UI re-renders the server's
 * returned values. The optimistic apply only reflects the directly edited field;
 * any rescaled siblings arrive from the server.
 */

import type { DerivedItem } from "@/api/derivedItems";

/** One editable field on a derived item. */
export interface EditableField {
  /** The `field` value sent in the `PATCH` body (canonical contract name). */
  readonly requestField: string;
  /** The DTO key holding the current (editable) value. */
  readonly currentKey: string;
  /**
   * The DTO key holding the immutable estimated/original snapshot, or `null`
   * when the field has none (food `quantity`/`amount` drives the rescale and is
   * not itself a snapshotted estimator output).
   */
  readonly estimatedKey: string | null;
  /** Short, compact label shown beside the value. */
  readonly label: string;
  /** Unit suffix for display (`"cal"`, `"g"`, or `""`). */
  readonly unit: string;
}

/**
 * Editable food fields, in display order. Mirrors the FTY-051 editable set:
 * `quantity` (the `amount`), `calories`, and the three macros. A `quantity` edit
 * is a single `PATCH` whose response may carry server-rescaled calories/macros.
 */
const FOOD_FIELDS: readonly EditableField[] = [
  {
    requestField: "quantity",
    currentKey: "amount",
    estimatedKey: null,
    label: "Servings",
    unit: "",
  },
  {
    requestField: "calories",
    currentKey: "calories",
    estimatedKey: "calories_estimated",
    label: "Calories",
    unit: "cal",
  },
  {
    requestField: "protein_g",
    currentKey: "protein_g",
    estimatedKey: "protein_g_estimated",
    label: "Protein",
    unit: "g",
  },
  {
    requestField: "carbs_g",
    currentKey: "carbs_g",
    estimatedKey: "carbs_g_estimated",
    label: "Carbs",
    unit: "g",
  },
  {
    requestField: "fat_g",
    currentKey: "fat_g",
    estimatedKey: "fat_g_estimated",
    label: "Fat",
    unit: "g",
  },
];

/** Editable exercise fields: the single active-calories burn override. */
const EXERCISE_FIELDS: readonly EditableField[] = [
  {
    requestField: "active_calories",
    currentKey: "active_calories",
    estimatedKey: "active_calories_estimated",
    label: "Burn",
    unit: "cal",
  },
];

/** The editable fields for an item, by its `item_type`. */
export function editFieldsFor(item: DerivedItem): readonly EditableField[] {
  return item.item_type === "food" ? FOOD_FIELDS : EXERCISE_FIELDS;
}

function numericField(item: DerivedItem, key: string): number | null {
  const value = (item as unknown as Record<string, unknown>)[key];
  return typeof value === "number" ? value : null;
}

/** The field's current (editable) value, or `null` when unresolved. */
export function fieldCurrentValue(
  item: DerivedItem,
  field: EditableField,
): number | null {
  return numericField(item, field.currentKey);
}

/** The field's estimated/original value, or `null` when it has no snapshot. */
export function fieldEstimatedValue(
  item: DerivedItem,
  field: EditableField,
): number | null {
  return field.estimatedKey ? numericField(item, field.estimatedKey) : null;
}

/**
 * Tolerance for the edited comparison. The server rounds current energy/macros
 * to 0.1; an epsilon well below that step keeps float representation noise from
 * reading as an edit while still catching any real correction.
 */
const EDIT_EPSILON = 1e-6;

/**
 * Whether a field's current value differs from its preserved estimate — the
 * signal behind the edited indicator. Fields with no estimate (food
 * `quantity`/`amount`) or no value are never marked edited.
 */
export function isFieldEdited(
  item: DerivedItem,
  field: EditableField,
): boolean {
  const estimated = fieldEstimatedValue(item, field);
  const current = fieldCurrentValue(item, field);
  if (estimated === null || current === null) {
    return false;
  }
  return Math.abs(current - estimated) > EDIT_EPSILON;
}

/** Whether any editable field on the item has been corrected. */
export function hasEdits(item: DerivedItem): boolean {
  return editFieldsFor(item).some((field) => isFieldEdited(item, field));
}

/**
 * Compact display string for a value: rounded to 0.1 and stripped of a trailing
 * `.0`, with `—` for an absent value. Matches the canonical 0.1 rounding the
 * backend applies so the UI never shows more precision than the server stores.
 */
export function formatValue(value: number | null): string {
  if (value === null) {
    return "—";
  }
  const rounded = Math.round(value * 10) / 10;
  return Number.isInteger(rounded) ? String(rounded) : rounded.toFixed(1);
}

/**
 * Apply a single-field override optimistically, before the server responds.
 * Only the directly edited field changes here; a `quantity` edit's rescaled
 * calories/macros are intentionally **not** computed locally — they arrive with
 * the server response and replace this optimistic item on success.
 */
export function optimisticApply(
  item: DerivedItem,
  field: EditableField,
  value: number,
): DerivedItem {
  return { ...item, [field.currentKey]: value } as DerivedItem;
}
