<template>
  <div class="app-container">
    <header class="app-header">
      <div class="logo">
        <el-icon :size="32" color="#667eea"><Document /></el-icon>
        <h1>Smart RAGFlow <span class="subtitle">文档管理</span></h1>
      </div>
      <div class="nav-links">
        <a href="http://localhost:3000" target="_blank" class="nav-link">
          <el-icon><ChatLineRound /></el-icon>
          问答系统
        </a>
      </div>
    </header>
    
    <main class="app-main">
      <DocumentManager />
    </main>
    
    <footer class="app-footer">
      <p>Smart RAGFlow 文档管理系统</p>
    </footer>
  </div>
</template>

<script setup>
import DocumentManager from './views/DocumentManager.vue'
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background: #f5f7fa;
}

.app-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  padding: 0 24px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  position: sticky;
  top: 0;
  z-index: 100;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo h1 {
  font-size: 20px;
  font-weight: 600;
  color: #333;
}

.logo .subtitle {
  font-size: 14px;
  color: #667eea;
  font-weight: normal;
  margin-left: 8px;
  padding-left: 8px;
  border-left: 2px solid #667eea;
}

.nav-links {
  display: flex;
  gap: 16px;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  color: #666;
  text-decoration: none;
  border-radius: 8px;
  transition: all 0.2s;
}

.nav-link:hover {
  background: #f0f7ff;
  color: #667eea;
}

.app-main {
  flex: 1;
  padding: 24px;
  max-width: 1400px;
  width: 100%;
  margin: 0 auto;
}

.app-footer {
  background: #fff;
  border-top: 1px solid #e4e7ed;
  padding: 16px 24px;
  text-align: center;
  color: #999;
  font-size: 14px;
}
</style>
