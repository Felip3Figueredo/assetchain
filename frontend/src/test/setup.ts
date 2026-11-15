import "@testing-library/jest-dom/vitest";

// Recharts needs ResizeObserver in jsdom
(globalThis as any).ResizeObserver = class { observe() {} unobserve() {} disconnect() {} };
