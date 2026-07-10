import type { ReactNode } from 'react';
import { motion, useReducedMotion } from 'framer-motion';

interface PageTransitionProps {
  children: ReactNode;
  className?: string;
  testId?: string;
}

const PAGE_EASE = [0.16, 1, 0.3, 1] as const;

export function PageTransition({ children, className, testId }: PageTransitionProps) {
  const reduceMotion = useReducedMotion();

  return (
    <motion.main
      id="main-content"
      data-testid={testId}
      className={className}
      initial={reduceMotion ? false : { opacity: 0, y: 10, scale: 0.995, filter: 'blur(2px)' }}
      animate={reduceMotion ? undefined : { opacity: 1, y: 0, scale: 1, filter: 'blur(0px)' }}
      exit={reduceMotion ? undefined : { opacity: 0, y: -6, scale: 0.998, filter: 'blur(1px)' }}
      transition={{ duration: 0.3, ease: PAGE_EASE }}
      style={{ willChange: reduceMotion ? undefined : 'transform, opacity, filter' }}
    >
      {children}
    </motion.main>
  );
}
