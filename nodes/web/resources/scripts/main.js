import "beercss";
import "material-dynamic-colors";
import 'gridstack/dist/gridstack.min.css';
import '@fortawesome/fontawesome-free/css/all.css';
import 'round-slider/dist/roundslider.min.css';
import jQuery from 'jquery';
window.$ = window.jQuery = jQuery;
import Node from "./Node.js";
import { createApp } from 'vue';
import { createWebHashHistory, createRouter } from 'vue-router'
import App from './App.vue';
import Dashboard from './views/Dashboard.vue';
import Gamepad from './views/Gamepad.vue';
import ServoDebug from './views/ServoDebug.vue';
import ServoControl from './components/ServoControl.vue';
import '../styles/main.css';

// Create a central store for widget and service data
const appState = {
  availableServos: [],
  gridStack: null,
  gridState: {},
  widgetsState: {},
  registerGridStack(grid) {
    this.gridStack = grid;
  },
  getGridStack() {
    return this.gridStack;
  },
  setServos(servos) {
    this.availableServos = servos;
  },
  getServos() {
    return this.availableServos;
  },
  updateWidgetsState(state) {
    this.widgetsState = state;
  },
  getWidgetsState() {
    return this.widgetsState;
  }
};

// Make state available to window for debugging only
window.appState = appState;

let theme = await ui("theme", "#ffd700");
let app = createApp(App);

// Register custom components globally
app.component('servo-control', ServoControl);

// Provide app state to all components
app.provide('appState', appState);
app.provide('node', Node);

// Store for available servos (legacy support - will be deprecated)
window.availableServos = [];

const router = createRouter({
    history: createWebHashHistory(),
    routes: [
        { path: '/', component: Dashboard },
        { path: '/gamepad/:index', name: 'gamepad',  component: Gamepad },
        { path: '/servo/:id', name: 'servo', component: ServoDebug }
    ],
});
app.use(router).mount('#app');
