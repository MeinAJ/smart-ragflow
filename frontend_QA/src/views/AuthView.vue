<template>
  <div class="auth-container">
    <div class="auth-box">
      <div class="auth-header">
        <div class="logo">🤖</div>
        <h1>Smart RAGFlow</h1>
        <p>智能问答系统</p>
      </div>
      
      <div class="auth-tabs">
        <button 
          :class="['tab-btn', { active: activeTab === 'login' }]"
          @click="activeTab = 'login'"
        >
          登录
        </button>
        <button 
          :class="['tab-btn', { active: activeTab === 'register' }]"
          @click="activeTab = 'register'"
        >
          注册
        </button>
      </div>
      
      <!-- 登录表单 -->
      <form v-if="activeTab === 'login'" class="auth-form" @submit.prevent="handleLogin">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="loginForm.username"
            type="text"
            placeholder="请输入用户名"
            required
            maxlength="50"
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="loginForm.password"
            type="password"
            placeholder="请输入密码"
            required
            maxlength="100"
          />
        </div>
        <button type="submit" class="submit-btn" :disabled="isLoading">
          <span v-if="isLoading" class="spinner"></span>
          <span v-else>登录</span>
        </button>
      </form>
      
      <!-- 注册表单 -->
      <form v-else class="auth-form" @submit.prevent="handleRegister">
        <div class="form-group">
          <label>用户名</label>
          <input 
            v-model="registerForm.username"
            type="text"
            placeholder="请输入用户名（3-50位）"
            required
            minlength="3"
            maxlength="50"
          />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input 
            v-model="registerForm.password"
            type="password"
            placeholder="请输入密码（至少6位）"
            required
            minlength="6"
            maxlength="100"
          />
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <input 
            v-model="registerForm.confirmPassword"
            type="password"
            placeholder="请再次输入密码"
            required
          />
        </div>
        <div class="form-group">
          <label>邮箱（可选）</label>
          <input 
            v-model="registerForm.email"
            type="email"
            placeholder="请输入邮箱"
            maxlength="100"
          />
        </div>
        <button type="submit" class="submit-btn" :disabled="isLoading">
          <span v-if="isLoading" class="spinner"></span>
          <span v-else>注册</span>
        </button>
      </form>
      
      <div v-if="error" class="error-message">
        {{ error }}
      </div>
      
      <div class="auth-footer">
        <p>测试账号：admin / admin123</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { login, register, isAuthenticated } from '../utils/auth.js'

const router = useRouter()
const activeTab = ref('login')
const isLoading = ref(false)
const error = ref('')

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  email: ''
})

// 如果已登录，跳转到首页
if (isAuthenticated()) {
  router.push('/')
}

const handleLogin = async () => {
  if (!loginForm.username || !loginForm.password) {
    error.value = '请填写完整信息'
    return
  }
  
  error.value = ''
  isLoading.value = true
  
  const result = await login({
    username: loginForm.username,
    password: loginForm.password
  })
  
  isLoading.value = false
  
  if (result.success) {
    router.push('/')
  } else {
    error.value = result.error
  }
}

const handleRegister = async () => {
  if (!registerForm.username || !registerForm.password) {
    error.value = '请填写完整信息'
    return
  }
  
  if (registerForm.password !== registerForm.confirmPassword) {
    error.value = '两次输入的密码不一致'
    return
  }
  
  if (registerForm.username.length < 3) {
    error.value = '用户名至少3位'
    return
  }
  
  if (registerForm.password.length < 6) {
    error.value = '密码至少6位'
    return
  }
  
  error.value = ''
  isLoading.value = true
  
  const data = {
    username: registerForm.username,
    password: registerForm.password
  }
  
  if (registerForm.email) {
    data.email = registerForm.email
  }
  
  const result = await register(data)
  
  isLoading.value = false
  
  if (result.success) {
    router.push('/')
  } else {
    error.value = result.error
  }
}
</script>

<style scoped>
.auth-container {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  padding: 20px;
}

.auth-box {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(10px);
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.auth-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo {
  font-size: 48px;
  margin-bottom: 12px;
}

.auth-header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #fff;
  margin: 0 0 8px;
}

.auth-header p {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.5);
  margin: 0;
}

.auth-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 24px;
  background: rgba(0, 0, 0, 0.2);
  border-radius: 12px;
  padding: 4px;
}

.tab-btn {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.tab-btn:hover {
  color: rgba(255, 255, 255, 0.8);
}

.tab-btn.active {
  background: rgba(102, 126, 234, 0.8);
  color: #fff;
}

.auth-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.7);
}

.form-group input {
  padding: 12px 16px;
  background: rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  color: #fff;
  font-size: 14px;
  outline: none;
  transition: all 0.2s;
}

.form-group input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.form-group input:focus {
  border-color: #667eea;
  background: rgba(0, 0, 0, 0.3);
}

.submit-btn {
  padding: 14px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 10px;
  color: #fff;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-top: 8px;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.4);
}

.submit-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.error-message {
  padding: 12px 16px;
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.3);
  border-radius: 10px;
  color: #f44336;
  font-size: 13px;
  margin-top: 16px;
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
}

.auth-footer p {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
}

@media (max-width: 480px) {
  .auth-box {
    padding: 24px;
  }
  
  .auth-header h1 {
    font-size: 24px;
  }
}
</style>
