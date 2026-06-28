import { useState } from "react";
import { act, create, type ReactTestRenderer } from "react-test-renderer";

import { useOfflineQueue, type OfflineQueue } from "./useOfflineQueue";
import type { OutboxEntry, OutboxStore } from "./outbox";
import type { LogEventDTO } from "@/api/logEvents";

const USER_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa";
const USER_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb";

function entry(overrides: Partial<OutboxEntry> = {}): OutboxEntry {
  return {
    idempotencyKey: "key-a",
    userId: USER_A,
    rawText: "two eggs",
    capturedAt: "2026-06-28T08:00:00Z",
    syncState: "queued",
    ...overrides,
  };
}

/** A controllable in-memory store, recording its calls. */
function makeStore(initial: Record<string, readonly OutboxEntry[]> = {}) {
  const data = new Map<string, readonly OutboxEntry[]>(Object.entries(initial));
  const cleared: string[] = [];
  const store: OutboxStore = {
    load: jest.fn(async (userId: string) => data.get(userId) ?? []),
    save: jest.fn(async (userId: string, entries: readonly OutboxEntry[]) => {
      data.set(userId, entries);
    }),
    clear: jest.fn(async (userId: string) => {
      cleared.push(userId);
      data.delete(userId);
    }),
  };
  return { store, cleared, data };
}

// Every tree created in a test, torn down in afterEach so a prior test's still-
// mounted hook can't fire a late setState (its drain/interval) outside the next
// test's act() and spam "update not wrapped in act" warnings.
const liveTrees: ReactTestRenderer[] = [];

afterEach(() => {
  act(() => {
    for (const tree of liveTrees.splice(0)) tree.unmount();
  });
});

/**
 * Renders the hook in a throwaway host component and exposes its latest return
 * value, plus a setter to drive a user transition (A → null → B).
 */
function renderQueue(opts: {
  initialUserId: string | null;
  store: OutboxStore;
  submit?: (entry: OutboxEntry) => Promise<LogEventDTO>;
  onAccepted?: (entry: OutboxEntry, event: LogEventDTO) => void;
}) {
  let latest!: OfflineQueue;
  let setUserId!: (id: string | null) => void;

  function Host(props: { initialUserId: string | null }) {
    const [userId, setId] = useState(props.initialUserId);
    setUserId = setId;
    latest = useOfflineQueue({
      userId,
      store: opts.store,
      submit:
        opts.submit ??
        (async () => {
          throw new Error("submit not expected in this test");
        }),
      onAccepted: opts.onAccepted ?? (() => {}),
    });
    return null;
  }

  let tree!: ReactTestRenderer;
  act(() => {
    tree = create(<Host initialUserId={opts.initialUserId} />);
  });
  liveTrees.push(tree);
  return {
    get current() {
      return latest;
    },
    setUserId: (id: string | null) =>
      act(() => {
        setUserId(id);
      }),
    unmount: () =>
      act(() => {
        const i = liveTrees.indexOf(tree);
        if (i >= 0) liveTrees.splice(i, 1);
        tree.unmount();
      }),
  };
}

// Let the async store.load()/save() promise chains settle inside act(), so the
// setState they trigger is wrapped and React emits no "not wrapped in act"
// warning. setImmediate drains the full microtask queue for the pending chain.
async function flush() {
  await act(async () => {
    await new Promise<void>((resolve) => setImmediate(() => resolve()));
  });
}

describe("useOfflineQueue user transitions", () => {
  it("clears the previous user's in-memory entries on a switch to a user with no stored backlog", async () => {
    // User A has a queued entry persisted; user B has nothing stored.
    const { store, cleared } = makeStore({ [USER_A]: [entry()] });
    const harness = renderQueue({ initialUserId: USER_A, store });
    await flush();

    expect(harness.current.entries).toHaveLength(1);
    expect(harness.current.reachability).toBe("offline");

    // Switch directly to user B (whose store.load resolves to []).
    harness.setUserId(USER_B);
    await flush();

    // A's queue is purged from disk, and — the fix — also evicted from memory,
    // so B never sees A's captures and the drain can't submit them under B.
    expect(cleared).toContain(USER_A);
    expect(harness.current.entries).toEqual([]);
    expect(harness.current.reachability).toBe("online");
  });

  it("never drains the previous user's entries after a switch", async () => {
    const submit = jest.fn();
    const { store } = makeStore({ [USER_A]: [entry()] });
    const harness = renderQueue({ initialUserId: USER_A, store, submit });
    await flush();

    harness.setUserId(USER_B);
    await flush();

    // drainNow must find no work for B — A's entry is gone from memory.
    act(() => harness.current.drainNow());
    await flush();
    expect(submit).not.toHaveBeenCalled();
  });

  it("loads the new user's own stored backlog after a switch", async () => {
    const { store } = makeStore({
      [USER_A]: [entry()],
      [USER_B]: [entry({ userId: USER_B, idempotencyKey: "key-b" })],
    });
    const harness = renderQueue({ initialUserId: USER_A, store });
    await flush();

    harness.setUserId(USER_B);
    await flush();

    expect(harness.current.entries).toHaveLength(1);
    expect(harness.current.entries[0]?.idempotencyKey).toBe("key-b");
    expect(harness.current.reachability).toBe("offline");
  });

  it("does not clear the durable queue on unmount (navigation away)", async () => {
    const { store, cleared } = makeStore({ [USER_A]: [entry()] });
    const harness = renderQueue({ initialUserId: USER_A, store });
    await flush();

    harness.unmount();
    expect(cleared).not.toContain(USER_A);
  });
});
