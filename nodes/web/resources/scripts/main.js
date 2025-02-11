import "beercss";
import "material-dynamic-colors";
import 'gridstack/dist/gridstack.min.css';
import '@fortawesome/fontawesome-free/css/all.css';
import Node from "./Node.js";
import { createApp } from 'vue';
import { createWebHashHistory, createRouter } from 'vue-router'
import App from './App.vue';
import Dashboard from './views/Dashboard.vue';
import Gamepad from './views/Gamepad.vue';
import '../styles/main.css';

let theme = await ui("theme", "#ffd700");
let app = createApp(App);
const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        { path: '/', component: Dashboard },
        { path: '/gamepad/:index', name: 'gamepad',  component: Gamepad }
    ],
});
app.use(router).mount('#app');