/**
 * Synaptiq Motion System — Animation & Transition Language
 *
 * Import from this file whenever you need animation values.
 * All interactions must stay under 200ms to feel responsive.
 *
 * Usage:
 *   import { transition, keyframes } from "@/lib/motion";
 *   style={{ transition: transition.hover }}
 */

// ── Duration scale ────────────────────────────────────────────────────────────
export const duration = {
  instant: 75,   // ms — immediate feedback (checkbox, toggle)
  fast:    120,  // ms — hover state changes
  base:    150,  // ms — standard transitions
  smooth:  200,  // ms — elements entering viewport
  enter:   250,  // ms — panels sliding in
  exit:    150,  // ms — panels leaving (always faster than enter)
  slow:    350,  // ms — complex layout shifts
};

// ── Easing curves ─────────────────────────────────────────────────────────────
export const ease = {
  default: "cubic-bezier(0.16, 1, 0.3, 1)",      // general purpose — fast out
  in:      "cubic-bezier(0.4, 0, 1, 1)",          // element leaving — accelerate
  out:     "cubic-bezier(0, 0, 0.2, 1)",          // element entering — decelerate
  inOut:   "cubic-bezier(0.4, 0, 0.2, 1)",        // symmetric
  spring:  "cubic-bezier(0.34, 1.56, 0.64, 1)",   // playful, slight overshoot
  snappy:  "cubic-bezier(0.2, 0, 0, 1)",          // Linear-style fast settle
  bounce:  "cubic-bezier(0.68, -0.55, 0.27, 1.55)", // bounce
};

// ── Transition presets ────────────────────────────────────────────────────────
// These are ready-to-paste CSS transition strings.
export const transition = {
  // Interaction states
  hover:       `border-color ${duration.base}ms ${ease.default}, box-shadow ${duration.base}ms ${ease.default}`,
  hoverCard:   `border-color ${duration.base}ms ${ease.default}, box-shadow ${duration.base}ms ${ease.default}, transform ${duration.fast}ms ${ease.default}`,
  hoverButton: `background ${duration.base}ms ${ease.default}, opacity ${duration.fast}ms ${ease.default}`,
  focus:       `border-color ${duration.fast}ms ${ease.default}, box-shadow ${duration.fast}ms ${ease.default}`,
  color:       `color ${duration.base}ms ${ease.default}`,
  colorFast:   `color ${duration.fast}ms ${ease.default}`,
  all:         `all ${duration.base}ms ${ease.default}`,

  // Enter / exit
  fadeIn:      `opacity ${duration.smooth}ms ${ease.out}`,
  slideUp:     `transform ${duration.enter}ms ${ease.out}, opacity ${duration.enter}ms ${ease.out}`,
  slideDown:   `transform ${duration.exit}ms ${ease.in}, opacity ${duration.exit}ms ${ease.in}`,
  scaleIn:     `transform ${duration.smooth}ms ${ease.spring}, opacity ${duration.smooth}ms ${ease.out}`,

  // Sidebar / drawer
  slideRight:  `transform ${duration.enter}ms ${ease.out}`,
  slideLeft:   `transform ${duration.exit}ms ${ease.in}`,
};

// ── CSS keyframe strings ──────────────────────────────────────────────────────
// Inject these into a <style> tag or CSS file when needed.
export const keyframes = {
  fadeIn: `
    @keyframes sqFadeIn {
      from { opacity: 0; }
      to   { opacity: 1; }
    }
  `,
  fadeInUp: `
    @keyframes sqFadeInUp {
      from { opacity: 0; transform: translateY(8px); }
      to   { opacity: 1; transform: translateY(0); }
    }
  `,
  scaleIn: `
    @keyframes sqScaleIn {
      from { opacity: 0; transform: scale(0.95); }
      to   { opacity: 1; transform: scale(1); }
    }
  `,
  shimmer: `
    @keyframes sqShimmer {
      0%   { background-position: -600px 0; }
      100% { background-position: 600px 0; }
    }
  `,
  pulse: `
    @keyframes sqPulse {
      0%, 100% { opacity: 1; }
      50%       { opacity: 0.4; }
    }
  `,
  spin: `
    @keyframes sqSpin {
      from { transform: rotate(0deg); }
      to   { transform: rotate(360deg); }
    }
  `,
};

// ── Animation class names ─────────────────────────────────────────────────────
// These assume the keyframes above are injected globally.
export const animate = {
  fadeIn:    `sqFadeIn ${duration.smooth}ms ${ease.out} both`,
  fadeInUp:  `sqFadeInUp ${duration.smooth}ms ${ease.out} both`,
  scaleIn:   `sqScaleIn ${duration.smooth}ms ${ease.spring} both`,
  shimmer:   `sqShimmer 1.6s ${ease.inOut} infinite`,
  pulse:     `sqPulse 1.5s ${ease.inOut} infinite`,
  spin:      `sqSpin 600ms linear infinite`,
};

// ── Transform presets ─────────────────────────────────────────────────────────
// Common transform values for hover lift, press-down effects.
export const transform = {
  liftSm:   "translateY(-1px)",
  lift:     "translateY(-2px)",
  liftLg:   "translateY(-4px)",
  pressSm:  "translateY(0) scale(0.99)",
  press:    "translateY(1px) scale(0.98)",
  none:     "translateY(0)",
};
