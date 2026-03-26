<template>
  <div class="app">
    <router-view />
  </div>
</template>

<script setup>
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans SC', sans-serif;
  background-color: #1a1a2e;
  color: #fff;
  line-height: 1.6;
}

.app {
  min-height: 100vh;
}

/* 全局滚动条样式 */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 全局选中样式 */
::selection {
  background: rgba(102, 126, 234, 0.3);
  color: #fff;
}

/* 全局链接样式 */
a {
  color: #667eea;
  text-decoration: none;
}

a:hover {
  color: #5a6fd6;
}

/* 全局按钮样式 */
button {
  font-family: inherit;
}

/* 全局输入框样式 */
input, textarea {
  font-family: inherit;
}
</style>
