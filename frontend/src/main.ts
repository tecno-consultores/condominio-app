import { createApp } from 'vue';
import { createPinia } from 'pinia';
import './assets/tokens.css';
import App from './App.vue';
import { initThemeMode } from './composables/useThemeMode';
import { buildAppRouter } from './router';

initThemeMode();

const app = createApp(App);
app.use(createPinia());
app.use(buildAppRouter());
app.mount('#app');
