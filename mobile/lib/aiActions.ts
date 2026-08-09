/**
 * The AI actions reachable from the orb.
 *
 * One source of truth shared by the menu that offers them and the Planner screen
 * that receives them as a route param. Keeping the ids here means a typo shows
 * up as a type error instead of a tap that silently does nothing.
 */

export type AiActionId = "capture" | "plan" | "review";

export type AiAction = {
  id: AiActionId;
  icon: string;
  label: string;
  description: string;
  /** Where it happens: on this screen, or the Planner tab. */
  target: "home" | "planner";
};

export const AI_ACTIONS: AiAction[] = [
  {
    id: "capture",
    icon: "＋",
    label: "Quick capture",
    description: "Turn a sentence into a scheduled task",
    target: "home",
  },
  {
    id: "plan",
    icon: "✨",
    label: "Plan my day",
    description: "Fill today's timeline around your calendar",
    target: "planner",
  },
  {
    id: "review",
    icon: "🌙",
    label: "Daily review",
    description: "See what slipped and roll it forward",
    target: "planner",
  },
];

/**
 * Read an action id off a route param.
 *
 * Params arrive as `string | string[] | undefined` from expo-router and are
 * user-controllable via deep link, so anything unrecognised must resolve to
 * null — a bad link should open the Planner normally, not crash it.
 */
export function parseAiAction(param: string | string[] | undefined): AiActionId | null {
  const value = Array.isArray(param) ? param[0] : param;
  const match = AI_ACTIONS.find((action) => action.id === value);
  return match ? match.id : null;
}

/**
 * The route to push for an action, or null when it runs on the current screen.
 *
 * Returns expo-router's object form rather than a hand-built URL string: the
 * typed-routes plugin checks `pathname` against the real route tree, so a
 * renamed screen becomes a compile error instead of a dead tap.
 */
export function routeForAction(
  id: AiActionId,
): { pathname: "/(tabs)/planner"; params: { action: AiActionId } } | null {
  const action = AI_ACTIONS.find((a) => a.id === id);
  if (!action || action.target === "home") return null;
  return { pathname: "/(tabs)/planner", params: { action: action.id } };
}
