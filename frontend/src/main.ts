import { createApp } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import { buildAppRouter } from './router';

const app = createApp(App);
app.use(createPinia());
app.use(buildAppRouter());
app.mount('#app');
