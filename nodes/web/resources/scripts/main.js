import "beercss";
import "material-dynamic-colors";
import 'gridstack/dist/gridstack.min.css';
import { GridStack } from 'gridstack';
import 'fontawesome';
import Node from "./Node.js";
import { createApp } from 'vue';

let theme = await ui("theme", "#ffd700");

let app = createApp({});

import Volume from './components/Volume';
import Sounds from './components/Sounds';
app.component('Sounds', Sounds);

app.mount('#app');

if (typeof(gridState) != 'object') {
    gridState = {};
}
const grid = GridStack.init({
    alwaysShowResizeHandle: 'mobile' // true if we're on mobile devices
});
if (gridState) {
    Object.keys(gridState).forEach((id) => {
        if (document.getElementById(id)) {
            grid.update(document.getElementById(id), gridState[id]);
        }
    })
}
grid.on('change', (event, items) => {
    items.forEach((item) => {
        gridState[item.el.id] = {
            x: parseInt(item.x),
            y: parseInt(item.y),
            h: parseInt(item.h),
            w: parseInt(item.w),
        }
    })
    node.sendOutput('save_grid_state', gridState);
});

// /* The Node component is now integrated as a Vue child component
//    which will emit events via its "event" event */

// function updateSoundList(sounds) {
//     var soundsList = document.getElementById('sounds');
//     soundsList.innerHTML = '';
//     if (!sounds || !Array.isArray(sounds)) return;
//     sounds.forEach(function(sound) {
//         var displayName = sound.replace(/\.mp3$/i, '');
//         var item = document.createElement('a');
//         item.style.cursor = 'pointer';
//         item.classList.add('row');
//         item.classList.add('wave');
//         item.innerText = displayName;
//         item.onclick = function() { node.sendOutput('play_sound', [sound]); };
//         soundsList.appendChild(item);
//     });
// }

// function setVolume(volume) {
//     node.sendOutput('set_volume', [volume]);
// }

// setInterval(() => {
//     if (node.ws.readyState === WebSocket.OPEN) {
//         document.getElementById('connection-active').style.display = '';
//         document.getElementById('connection-inactive').style.display = 'none';
//     } else {
//         document.getElementById('connection-active').style.display = 'none';
//         document.getElementById('connection-inactive').style.display = '';
//     }
// }, 100);

// node.next((event) => {
//     console.log(event);
//     if (event.id === 'available_sounds') {
//         updateSoundList(event.value);
//     }

//     if (event.id === 'voltage') {
//         document.getElementById('voltage').innerText = "Voltage: " + parseFloat(event.value).toFixed(2) + " V";
//     }

//     if (event.id === 'current') {
//         document.getElementById('current').innerText = "Current: " + parseFloat(event.value).toFixed(2) + " A";
//     }

//     if (event.id === 'power') {
//         document.getElementById('power').innerText = "Power: " + parseFloat(event.value).toFixed(2) + " W";
//     }

//     if (event.id === 'soc') {
//         document.getElementById('soc').innerText = parseFloat(event.value).toFixed(0) + " %";
//     }

//     if (event.id === 'runtime') {
//         document.getElementById('runtime').innerText = "Runtime: " + event.value;
//     }

//     if (event.id === 'shutdown') {
//         console.log('Shutdown event received:', event.value);
//     }

//     if (event.id === 'volume') {
//         document.getElementById('volume').value = event.volume;
//     }
// })

// window.addEventListener('DOMContentLoaded', () => {
//     document.querySelectorAll('.slider input[type="range"]').forEach(input => {
//         input.dispatchEvent(new Event('change'));
//     });
// });
