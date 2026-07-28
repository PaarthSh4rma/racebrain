import { defineConfig } from "@playwright/test";

const externalBaseUrl = process.env.PLAYWRIGHT_BASE_URL;

export default defineConfig({
  testDir: "./tests",
  fullyParallel: false,
  reporter: "line",
  webServer: externalBaseUrl
    ? undefined
    : {
        command: "npm run build && npm run preview -- --host 127.0.0.1 --port 4173",
        url: "http://127.0.0.1:4173",
        reuseExistingServer: false,
      },
  use: {
    baseURL: externalBaseUrl ?? "http://127.0.0.1:4173",
    browserName: "chromium",
    headless: true,
    viewport: { width: 390, height: 844 },
  },
});
