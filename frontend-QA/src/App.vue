<template>
  <div class="app">
    <header class="header">
      <h1>Smart RAGFlow</h1>
      <p class="subtitle">智能问答系统</p>
    </header>
    <main class="main">
      <ChatView />
    </main>
  </div>
</template>

<script setup>
import ChatView from './views/ChatView.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: #f5f5f5;
  color: #333;
}

.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 20px;
  text-align: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.header h1 {
  font-size: 24px;
  font-weight: 600;
}

.subtitle {
  font-size: 14px;
  opacity: 0.9;
  margin-top: 5px;
}

.main {
  flex: 1;
  display: flex;
  justify-content: center;
  padding: 20px;
}
</style>
