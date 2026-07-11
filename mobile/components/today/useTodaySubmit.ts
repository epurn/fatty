import { useEffect, useMemo, useRef, useState, type Dispatch, type SetStateAction } from "react";

import { type DerivedItem } from "@/api/derivedItems";
import {
  createLogEvent as createLogEventApi,
  type LogEventDTO,
} from "@/api/logEvents";
import { type SavedFoodDTO } from "@/api/savedFoods";
import { type OutboxStore } from "@/state/outbox";
import type { ApiSession } from "@/state/session";
import { sortByNewest } from "@/state/today";
import { useSubmitLog, type SubmitLogBridge } from "@/state/useSubmitLog";

import { removeOptimisticEvent, syntheticSavedFoodItem } from "./helpers";

/** The Today-state seams the submit-bridge writes through. */
export type UseTodaySubmitParams = {
  /** The authenticated session, or null when signed out. */
  apiSession: ApiSession | null;
  /** Today's optimistic event list setter. */
  setEvents: Dispatch<SetStateAction<readonly LogEventDTO[]>>;
  /** Today's item-by-event map setter (for the saved-food synthetic item). */
  setItemsByEvent: Dispatch<
    SetStateAction<Readonly<Record<string, readonly DerivedItem[]>>>
  >;
  /** Injectable create endpoint for tests. */
  create: typeof createLogEventApi;
  /** Durable offline-outbox storage (FTY-104) — injectable for tests. */
  outboxStore: OutboxStore;
  /** Reconnect-retry cadence for the outbox drain — injectable for tests. */
  retryIntervalMs?: number;
  /** Idempotency-key generator — injectable for deterministic tests. */
  generateKey: () => string;
  /** Current-timestamp source — injectable for deterministic tests. */
  now: () => string;
};

/**
 * The Today submit-bridge (FTY-053/147, extracted in FTY-352). It owns the
 * saved-food selection glue that sits between Today's optimistic timeline and
 * the shared submit machine ({@link useSubmitLog}): the selected saved food and
 * its synchronous ref, the per-optimistic-id saved-food map used to re-key on
 * success / restore on rollback, and the {@link SubmitLogBridge} callbacks that
 * add the synthetic saved-food item so the estimator is skipped for a saved
 * food. `useTodayData` composes this hook and re-exposes its return surface
 * unchanged; the machine stays screen-agnostic behind the bridge.
 */
export function useTodaySubmit({
  apiSession,
  setEvents,
  setItemsByEvent,
  create,
  outboxStore,
  retryIntervalMs,
  generateKey,
  now,
}: UseTodaySubmitParams) {
  // Saved food selected from the typeahead bar (FTY-053). When set, pressing
  // "Add" creates the log event AND immediately adds a synthetic resolved item
  // with the saved food's nutrition, skipping the estimator wait.
  const [selectedSavedFood, setSelectedSavedFood] = useState<SavedFoodDTO | null>(null);

  // The submit machine reads the latest selected saved food at submit time, and
  // each in-flight submit stashes its saved food by optimistic id so the right
  // one is re-keyed on success / restored on a server-error rollback. The ref is
  // synced in an effect (never during render) per the project's ref convention.
  const selectedSavedFoodRef = useRef<SavedFoodDTO | null>(null);
  useEffect(() => {
    selectedSavedFoodRef.current = selectedSavedFood;
  });
  const pendingSavedFoodById = useRef(new Map<string, SavedFoodDTO | null>());

  // Quick-add suggestions refresh (FTY-341), called from the submit-success path
  // below. Held behind a ref so the memoized submit bridge never re-creates.
  const refreshSuggestionsRef = useRef<() => void>(() => {});

  // Today's optimistic-timeline operations, handed to the shared submit machine
  // (FTY-147). The machine owns create/optimistic/offline/rollback; the
  // saved-food synthetic item (FTY-053) stays here, behind these callbacks.
  const submitBridge = useMemo<SubmitLogBridge>(
    () => ({
      insertOptimistic(optimistic) {
        setEvents((prev) => sortByNewest([optimistic, ...prev]));
        const savedFood = selectedSavedFoodRef.current;
        pendingSavedFoodById.current.set(optimistic.id, savedFood);
        // A selected saved food carries resolved nutrition immediately — add a
        // synthetic resolved item so the estimator is bypassed for this entry.
        if (savedFood && apiSession) {
          const syntheticItem = syntheticSavedFoodItem(
            savedFood,
            optimistic.id,
            apiSession.userId,
          );
          setItemsByEvent((prev) => ({ ...prev, [optimistic.id]: [syntheticItem] }));
        }
        setSelectedSavedFood(null);
      },
      reconcileOptimistic(optimisticId, server) {
        setEvents((prev) =>
          sortByNewest(
            prev.map((event) => (event.id === optimisticId ? server : event)),
          ),
        );
        setItemsByEvent((prev) => {
          const items = prev[optimisticId];
          if (!items) return prev;
          const updated = items.map((item) => ({
            ...item,
            log_event_id: server.id,
          }));
          const { [optimisticId]: _removed, ...rest } = prev;
          return { ...rest, [server.id]: updated };
        });
        pendingSavedFoodById.current.delete(optimisticId);
        // Refresh quick-add suggestions (FTY-341): the rank just changed.
        refreshSuggestionsRef.current();
      },
      rollbackOptimistic(optimisticId) {
        removeOptimisticEvent(setEvents, setItemsByEvent, optimisticId);
        // Restore the saved-food association so retry is one tap (server error).
        const savedFood = pendingSavedFoodById.current.get(optimisticId) ?? null;
        pendingSavedFoodById.current.delete(optimisticId);
        if (savedFood) setSelectedSavedFood(savedFood);
      },
      discardOptimistic(optimisticId) {
        // Unreachable: the capture is kept as an offline row, not restored to the
        // composer — so the saved-food association is dropped, not restored.
        removeOptimisticEvent(setEvents, setItemsByEvent, optimisticId);
        pendingSavedFoodById.current.delete(optimisticId);
      },
      acceptDrained(_idempotencyKey, event) {
        // A drained offline capture folds into the normal flow: insert the real
        // server event (deduped by id) and let polling reconcile it to terminal.
        setEvents((prev) =>
          sortByNewest([event, ...prev.filter((e) => e.id !== event.id)]),
        );
      },
    }),
    [apiSession, setEvents, setItemsByEvent],
  );

  const submit = useSubmitLog({
    session: apiSession,
    bridge: submitBridge,
    create,
    outboxStore,
    retryIntervalMs,
    generateKey,
    now,
  });

  return {
    ...submit,
    selectedSavedFood,
    setSelectedSavedFood,
    selectedSavedFoodRef,
    refreshSuggestionsRef,
  };
}
