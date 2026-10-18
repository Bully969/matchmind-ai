import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
export default defineConfig({ plugins: [react()], test: { include: ['src/test/**/*.test.{js,jsx}'], environment: 'jsdom', setupFiles: ['./src/test/setup.js'], restoreMocks: true }, server: { host: '0.0.0.0' } });
