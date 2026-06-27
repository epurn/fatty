import {
  DerivedItemApiError,
  editDerivedItem,
  type DerivedFoodItemDTO,
  type DerivedItemSession,
} from "./derivedItems";

const SESSION: DerivedItemSession = {
  baseUrl: "https://api.example.test",
  token: "test-token",
  userId: "11111111-1111-1111-1111-111111111111",
};

const FOOD: DerivedFoodItemDTO = {
  item_type: "food",
  id: "44444444-4444-4444-4444-444444444444",
  user_id: SESSION.userId,
  log_event_id: "55555555-5555-5555-5555-555555555555",
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
};

function okResponse(body: unknown, status = 200): Response {
  return {
    ok: true,
    status,
    json: async () => body,
  } as unknown as Response;
}

function errorResponse(status: number, body: unknown = { detail: "error" }): Response {
  return {
    ok: false,
    status,
    json: async () => body,
  } as unknown as Response;
}

describe("editDerivedItem", () => {
  it("PATCHes the field/value to the owner's item endpoint with a bearer token", async () => {
    const updated = { ...FOOD, calories: 200, calories_estimated: 150 };
    const fetchMock = jest.fn().mockResolvedValue(okResponse(updated));

    const result = await editDerivedItem(
      SESSION,
      "food",
      FOOD.id,
      "calories",
      200,
      fetchMock,
    );

    expect(result).toEqual(updated);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "https://api.example.test/api/users/11111111-1111-1111-1111-111111111111/derived-items/food/44444444-4444-4444-4444-444444444444",
    );
    expect(init.method).toBe("PATCH");
    const headers = init.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer test-token");
    expect(headers["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({
      field: "calories",
      value: 200,
    });
  });

  it("addresses the exercise item type in the path", async () => {
    const fetchMock = jest.fn().mockResolvedValue(
      okResponse({
        ...FOOD,
        item_type: "exercise",
        active_calories: 120,
        active_calories_estimated: 100,
      }),
    );

    await editDerivedItem(SESSION, "exercise", "abc", "active_calories", 120, fetchMock);

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/derived-items/exercise/abc");
  });

  it("returns the server's rescaled item for a quantity edit verbatim", async () => {
    // The server rescales calories/macros on a servings edit; the client just
    // returns what it gets — it never computes the rescale.
    const rescaled = {
      ...FOOD,
      amount: 2,
      calories: 300,
      protein_g: 40,
      carbs_g: 16,
      fat_g: 8,
    };
    const fetchMock = jest.fn().mockResolvedValue(okResponse(rescaled));

    const result = await editDerivedItem(SESSION, "food", FOOD.id, "quantity", 2, fetchMock);

    expect(result).toEqual(rescaled);
  });

  it("maps a 401 to a session-expired error", async () => {
    const fetchMock = jest.fn().mockResolvedValue(errorResponse(401));
    await expect(
      editDerivedItem(SESSION, "food", FOOD.id, "calories", 1, fetchMock),
    ).rejects.toMatchObject({ name: "DerivedItemApiError", status: 401 });
  });

  it("maps a 404 (cross-user/unknown item, fail closed) to an error", async () => {
    const fetchMock = jest.fn().mockResolvedValue(errorResponse(404));
    await expect(
      editDerivedItem(SESSION, "food", FOOD.id, "calories", 1, fetchMock),
    ).rejects.toBeInstanceOf(DerivedItemApiError);
  });

  it("maps a 422 to a nonjudgmental error that never echoes the value", async () => {
    // The server's 422 carries a machine code; the client message must not leak
    // the field name's value or any number the user entered.
    const fetchMock = jest.fn().mockResolvedValue(
      errorResponse(422, { detail: { error: "out_of_range", field: "calories" } }),
    );
    try {
      await editDerivedItem(SESSION, "food", FOOD.id, "calories", 999999, fetchMock);
      throw new Error("expected editDerivedItem to throw");
    } catch (error) {
      expect(error).toBeInstanceOf(DerivedItemApiError);
      const message = (error as DerivedItemApiError).message;
      expect((error as DerivedItemApiError).status).toBe(422);
      expect(message).not.toContain("999999");
    }
  });
});
