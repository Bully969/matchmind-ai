import { defineConfig, devices } from '@playwright/test';
export default defineConfig({
  testDir: './e2e', timeout: 30000, retries: 0,
  reporter: [['list'], ['html', {open:'never'}]],
  use: {baseURL:'http://127.0.0.1:4173', trace:'retain-on-failure'},
  projects: [
    {name:'desktop-chromium',use:{...devices['Desktop Chrome']}},
    {name:'iphone-webkit',use:{...devices['iPhone 13']}},
  ],
  webServer:{command:'npm run dev -- --host 127.0.0.1 --port 4173',url:'http://127.0.0.1:4173',reuseExistingServer:!process.env.CI},
});
