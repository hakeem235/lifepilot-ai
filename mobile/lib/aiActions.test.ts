import { describe, expect, it } from "vitest";

import { AI_ACTIONS, parseAiAction, routeForAction } from "./aiActions";

describe("AI_ACTIONS", () => {
  it("has unique ids", () => {
    const ids = AI_ACTIONS.map((a) => a.id);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("gives every action a label and a description", () => {
    for (const action of AI_ACTIONS) {
      expect(action.label.length).toBeGreaterThan(0);
      expect(action.description.length).toBeGreaterThan(0);
    }
  });
});

describe("parseAiAction", () => {
  it("accepts every declared action id", () => {
    for (const action of AI_ACTIONS) {
      expect(parseAiAction(action.id)).toBe(action.id);
    }
  });

  it("takes the first value when expo-router hands back an array", () => {
    expect(parseAiAction(["plan", "review"])).toBe("plan");
  });

  it("rejects unknown, empty and missing params rather than throwing", () => {
    // These arrive from deep links, so they are attacker-controllable input.
    expect(parseAiAction("drop-tables")).toBeNull();
    expect(parseAiAction("")).toBeNull();
    expect(parseAiAction(undefined)).toBeNull();
    expect(parseAiAction([])).toBeNull();
  });
});

describe("routeForAction", () => {
  it("returns null for actions that run on the current screen", () => {
    expect(routeForAction("capture")).toBeNull();
  });

  it("routes planner actions with the action param attached", () => {
    expect(routeForAction("plan")).toEqual({
      pathname: "/(tabs)/planner",
      params: { action: "plan" },
    });
    expect(routeForAction("review")).toEqual({
      pathname: "/(tabs)/planner",
      params: { action: "review" },
    });
  });

  it("round-trips: every route it builds parses back to the same action", () => {
    for (const action of AI_ACTIONS) {
      const route = routeForAction(action.id);
      if (!route) continue;
      expect(parseAiAction(route.params.action)).toBe(action.id);
    }
  });
});
