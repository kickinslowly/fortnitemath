import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: '.',
  testMatch: /.*\.spec\.mjs/,
  outputDir: './test-results',
  reporter: 'list',
  fullyParallel: true,
  use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 800 } },
});
