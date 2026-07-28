import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  reporter: "line",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "https://racebrain-mauve.vercel.app",
    browserName: "chromium",
    channel: "chrome",
    headless: true,
    viewport: { width: 390, height: 844 },
  },
});
