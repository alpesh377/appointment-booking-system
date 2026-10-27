"use client";

import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import * as React from "react";

/**
 * Motion toolkit shared by all pages. Every helper turns into a plain element
 * (or strips its animation) when the OS requests reduced motion, so content
 * and controls are identical with or without animation.
 */
const EASE_OUT = [0.16, 1, 0.3, 1] as const;

const enter = { opacity: 0, y: 6 };
const entered = { opacity: 1, y: 0 };

/**
 * A short, subtle entrance. `MotionConfig reducedMotion="user"` and
 * `useReducedMotion` both honour the operating-system preference.
 */
export function FadeIn({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? undefined : enter}
      animate={reduce ? undefined : entered}
      transition={{ duration: 0.2, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Staggers direct children on first render. Items render un-animated when
 * reduced motion is requested; the delay is capped so long lists do not
 * cascade noticeably.
 */
export function StaggerGroup({
  children,
  className,
  stagger = 0.04,
  maxDelay = 0.36,
}: {
  children: React.ReactNode;
  className?: string;
  stagger?: number;
  maxDelay?: number;
}) {
  const reduce = useReducedMotion();
  if (reduce) return <div className={className}>{children}</div>;

  return (
    <div className={className}>
      {React.Children.map(children, (child, index) => {
        if (!React.isValidElement(child) || child.type === StaggerItem) {
          return child;
        }
        return <StaggerItem delay={Math.min(index * stagger, maxDelay)}>{child}</StaggerItem>;
      })}
    </div>
  );
}

export function StaggerItem({
  children,
  className,
  delay = 0,
}: {
  children: React.ReactNode;
  className?: string;
  delay?: number;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? undefined : enter}
      animate={reduce ? undefined : entered}
      transition={{ duration: 0.2, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Press + optional hover-lift feedback for cards and slot buttons. The
 * transform stays small so focus rings and layout never shift.
 */
export function Pressable({
  children,
  className,
  lift = false,
}: {
  children: React.ReactNode;
  className?: string;
  lift?: boolean;
}) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      tabIndex={-1}
      whileHover={reduce || !lift ? undefined : { y: -2 }}
      whileTap={reduce ? undefined : { scale: 0.985 }}
      transition={{ duration: 0.15, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

/**
 * Fades content out and in whenever `swapKey` changes — used for lists whose
 * underlying query changes (search results, slot grid).
 */
export function Swap({
  swapKey,
  children,
  className,
}: {
  swapKey: string;
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.div
        key={swapKey}
        className={className}
        initial={reduce ? undefined : { opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={reduce ? undefined : { opacity: 0 }}
        transition={{ duration: 0.15, ease: EASE_OUT }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/**
 * A sliding shared-layout pill rendered behind the currently selected choice
 * within a group. Render one per selectable item; sibling `layoutId`s must
 * match so the pill glides between items.
 */
export function SelectionHighlight({
  layoutId,
  className,
}: {
  layoutId: string;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return reduce ? (
    <span aria-hidden className={className} />
  ) : (
    <motion.span
      aria-hidden
      layoutId={layoutId}
      className={className}
      transition={{ duration: 0.2, ease: EASE_OUT }}
    />
  );
}

/**
 * Cross-fades/flips between states keyed by `statusKey`, e.g. an appointment
 * status badge changing value.
 */
export function StatusBadge({
  statusKey,
  children,
  className,
}: {
  statusKey: string;
  children: React.ReactNode;
  className?: string;
}) {
  const reduce = useReducedMotion();
  return (
    <AnimatePresence mode="popLayout" initial={false}>
      <motion.span
        key={statusKey}
        className={className}
        initial={reduce ? undefined : { opacity: 0, y: -8 }}
        animate={reduce ? undefined : { opacity: 1, y: 0 }}
        exit={reduce ? undefined : { opacity: 0, y: 8 }}
        transition={{ duration: 0.18, ease: EASE_OUT }}
      >
        {children}
      </motion.span>
    </AnimatePresence>
  );
}
