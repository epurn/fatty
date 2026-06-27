import type {
  DerivedExerciseItemDTO,
  DerivedFoodItemDTO,
} from "@/api/derivedItems";

import {
  editFieldsFor,
  fieldCurrentValue,
  fieldEstimatedValue,
  formatValue,
  hasEdits,
  isFieldEdited,
  optimisticApply,
  type EditableField,
} from "./derivedItems";

function food(overrides: Partial<DerivedFoodItemDTO> = {}): DerivedFoodItemDTO {
  return {
    item_type: "food",
    id: "food-1",
    user_id: "u1",
    log_event_id: "e1",
    name: "Greek yogurt",
    quantity_text: "1 cup",
    unit: "cup",
    amount: 1,
    status: "resolved",
    grams: 245,
    calories: 150,
    protein_g: 20,
    carbs_g: 8,
    fat_g: 4,
    calories_estimated: 150,
    protein_g_estimated: 20,
    carbs_g_estimated: 8,
    fat_g_estimated: 4,
    created_at: "2026-06-26T08:00:00Z",
    updated_at: "2026-06-26T08:00:00Z",
    ...overrides,
  };
}

function exercise(
  overrides: Partial<DerivedExerciseItemDTO> = {},
): DerivedExerciseItemDTO {
  return {
    item_type: "exercise",
    id: "ex-1",
    user_id: "u1",
    log_event_id: "e1",
    name: "Running",
    quantity_text: "30 min",
    unit: "min",
    amount: 30,
    status: "resolved",
    active_calories: 300,
    active_calories_estimated: 300,
    created_at: "2026-06-26T08:00:00Z",
    updated_at: "2026-06-26T08:00:00Z",
    ...overrides,
  };
}

const fieldByName = (
  fields: readonly EditableField[],
  requestField: string,
): EditableField => {
  const found = fields.find((f) => f.requestField === requestField);
  if (!found) {
    throw new Error(`missing field ${requestField}`);
  }
  return found;
};

describe("editFieldsFor", () => {
  it("exposes the food editable set: quantity, calories, and three macros", () => {
    const fields = editFieldsFor(food()).map((f) => f.requestField);
    expect(fields).toEqual(["quantity", "calories", "protein_g", "carbs_g", "fat_g"]);
  });

  it("exposes only active_calories for an exercise item", () => {
    const fields = editFieldsFor(exercise()).map((f) => f.requestField);
    expect(fields).toEqual(["active_calories"]);
  });
});

describe("fieldCurrentValue / fieldEstimatedValue", () => {
  it("reads the current value and the preserved estimate for a macro", () => {
    const item = food({ protein_g: 30, protein_g_estimated: 20 });
    const field = fieldByName(editFieldsFor(item), "protein_g");
    expect(fieldCurrentValue(item, field)).toBe(30);
    expect(fieldEstimatedValue(item, field)).toBe(20);
  });

  it("maps the quantity field to amount and has no estimated snapshot", () => {
    const item = food({ amount: 2 });
    const field = fieldByName(editFieldsFor(item), "quantity");
    expect(fieldCurrentValue(item, field)).toBe(2);
    expect(fieldEstimatedValue(item, field)).toBeNull();
  });

  it("returns null for an unresolved (null) value", () => {
    const item = food({ calories: null });
    const field = fieldByName(editFieldsFor(item), "calories");
    expect(fieldCurrentValue(item, field)).toBeNull();
  });
});

describe("isFieldEdited", () => {
  it("is false when the current value equals the estimate", () => {
    const item = food();
    const field = fieldByName(editFieldsFor(item), "calories");
    expect(isFieldEdited(item, field)).toBe(false);
  });

  it("is true when the current value differs from the estimate", () => {
    const item = food({ calories: 200, calories_estimated: 150 });
    const field = fieldByName(editFieldsFor(item), "calories");
    expect(isFieldEdited(item, field)).toBe(true);
  });

  it("is never edited for quantity, which has no estimate to compare", () => {
    const item = food({ amount: 5 });
    const field = fieldByName(editFieldsFor(item), "quantity");
    expect(isFieldEdited(item, field)).toBe(false);
  });

  it("ignores sub-epsilon float noise below the 0.1 rounding step", () => {
    const item = food({ fat_g: 4 + 1e-9, fat_g_estimated: 4 });
    const field = fieldByName(editFieldsFor(item), "fat_g");
    expect(isFieldEdited(item, field)).toBe(false);
  });

  it("hasEdits reports whether any field was corrected", () => {
    expect(hasEdits(food())).toBe(false);
    expect(hasEdits(food({ carbs_g: 12, carbs_g_estimated: 8 }))).toBe(true);
  });
});

describe("formatValue", () => {
  it("drops a trailing .0 and renders an absent value as a dash", () => {
    expect(formatValue(450)).toBe("450");
    expect(formatValue(7.5)).toBe("7.5");
    expect(formatValue(7.25)).toBe("7.3");
    expect(formatValue(null)).toBe("—");
  });
});

describe("optimisticApply", () => {
  it("sets only the edited field and leaves siblings for the server to rescale", () => {
    const item = food();
    const quantity = fieldByName(editFieldsFor(item), "quantity");
    const next = optimisticApply(item, quantity, 2) as DerivedFoodItemDTO;
    // The amount updates immediately; calories/macros are NOT locally rescaled —
    // the server returns the rescaled values.
    expect(next.amount).toBe(2);
    expect(next.calories).toBe(150);
    expect(next.protein_g).toBe(20);
  });

  it("overrides a direct field without touching the estimate", () => {
    const item = food();
    const calories = fieldByName(editFieldsFor(item), "calories");
    const next = optimisticApply(item, calories, 200) as DerivedFoodItemDTO;
    expect(next.calories).toBe(200);
    expect(next.calories_estimated).toBe(150);
  });
});
