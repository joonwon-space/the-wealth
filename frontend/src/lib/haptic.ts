/**
 * Thin wrapper around navigator.vibrate that is safe in SSR and on browsers
 * (Safari, most iOS) that don't support the Vibration API. All calls become
 * no-ops outside a browser context or when the API is missing.
 */

type Pattern = number | number[];

export function vibrate(pattern: Pattern = 10): void {
  if (typeof navigator === "undefined") return;
  if (typeof navigator.vibrate !== "function") return;
  try {
    navigator.vibrate(pattern);
  } catch {
    // Some browsers throw when the device is in a low-power mode.
  }
}

export const haptic = {
  light: () => vibrate(8),
  medium: () => vibrate(14),
  heavy: () => vibrate([20, 10, 20]),
  success: () => vibrate([10, 40, 10]),
  warning: () => vibrate([30, 40, 30]),
};
