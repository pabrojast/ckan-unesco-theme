import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {fileURLToPath, URL} from 'node:url';

// IHP-WINS edition of DACS Community.
// - The Firebase SDK is replaced by shims/ that call the CKAN community API (ckanext/theme_ejemplo/community.py).
// - The build goes straight into the theme's public folder, served by CKAN at /dacs-community/.
//   Images, video, logos and templates already live there (assets/), so publicDir is off and bundles go to bundle/.
// - CKAN serves the hub page at /group/dacs/community-of-practice (it injects window.__DACS__);
//   the logo desk and the public report form are opened as static pages under /dacs-community/logo-desk/.
const outDir = fileURLToPath(new URL('../../ckanext/theme_ejemplo/public/dacs-community', import.meta.url));

export default defineConfig({
  base: '/dacs-community/',
  publicDir: false,
  plugins: [react()],
  build: {
    outDir,
    emptyOutDir: false,
    assetsDir: 'bundle',
    rollupOptions: {
      input: {
        hub: fileURLToPath(new URL('./index.html', import.meta.url)),
        logo: fileURLToPath(new URL('./logo-desk/index.html', import.meta.url)),
        report: fileURLToPath(new URL('./logo-desk/report.html', import.meta.url)),
      },
    },
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('.', import.meta.url)),
      'firebase/app': fileURLToPath(new URL('./shims/app.js', import.meta.url)),
      'firebase/auth': fileURLToPath(new URL('./shims/auth.js', import.meta.url)),
      'firebase/firestore': fileURLToPath(new URL('./shims/firestore.js', import.meta.url)),
    },
  },
});
