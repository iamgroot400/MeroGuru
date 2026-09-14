import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./tests",
  fullyParallel: true,
  workers: 2,
  timeout: 60000,
  use: {
    baseURL: "http://127.0.0.1:3000",
    browserName: "chromium",
    channel: "msedge",
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: "npm run dev",
    url: "http://127.0.0.1:3000",
    reuseExistingServer: !process.env.CI,
  },
});
