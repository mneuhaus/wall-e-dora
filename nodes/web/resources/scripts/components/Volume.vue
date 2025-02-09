<template>
  <button>
    <span><i class="fa-solid fa-volume-high"></i></span>
    <i>arrow_drop_down</i>
    <menu>
      <article class="small-height round">
        <label class="slider max vertical">
          <input type="range" id="volume" min="0" max="1" value="1" step="0.01" onchange="window.node.send_output('set_volume', [this.value]);">
          <span></span>
        </label>
      </article>
    </menu>
  </button>
</template>