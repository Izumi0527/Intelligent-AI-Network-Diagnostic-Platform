import { createApp, type Component } from 'vue';
import { createPinia } from 'pinia';
import App from './App.vue';
import './assets/main.css';

// .vue SFC 在 ESLint 解析下无法完整推断为 Component 类型（与运行时 vue-tsc 解析路径不同），
// 显式断言为 Component 提供给 ESLint 一个明确类型边界
const app = createApp(App as Component);
const pinia = createPinia();

app.use(pinia);
app.mount('#app');
