/*
 * The dot-matrix bar language shared by the hero chart and the accents elsewhere:
 * a bar runs from sparse dots through a checkerboard into a solid block.
 */

/** The hero chart's full palette. */
export const COLORS = ["#C9CBF2", "#3FD3DE", "#F05BAA", "#7CD94F", "#F2683A", "#A56EF7", "#EE4B44", "#F6B636", "#4B8EF3", "#3ED896"];

/**
 * Outside the hero, only colours that carry no status: green, amber and red mean
 * GO, RISKY and NO-GO everywhere else on the page.
 */
export const CALM = ["#3FD3DE", "#A56EF7", "#F05BAA", "#4B8EF3", "#C9CBF2"];

export const CELL = 6;

export const sparse = (color: string, cell = CELL) => `conic-gradient(${color} 25%, transparent 0) 0 0 / ${cell}px ${cell}px`;

export const checker = (color: string, cell = CELL) =>
  `conic-gradient(${color} 25%, transparent 0 50%, ${color} 0 75%, transparent 0) 0 0 / ${cell}px ${cell}px`;
