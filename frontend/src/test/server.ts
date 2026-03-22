/**
 * MSW Node server for Vitest (jsdom environment).
 * Import and use in test files or setup.ts.
 */
import { setupServer } from "msw/node";
import { handlers } from "./handlers";

export const server = setupServer(...handlers);
