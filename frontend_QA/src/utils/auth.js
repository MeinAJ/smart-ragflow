/**
 * 用户认证工具模块
 */

const TOKEN_KEY = 'access_token'
const USER_KEY = 'user_info'

/**
 * 保存登录凭证
 * @param {string} token - JWT Token
 * @param {object} user - 用户信息
 */
export function setAuth(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

/**
 * 获取 Token
 * @returns {string|null}
 */
export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

/**
 * 获取用户信息
 * @returns {object|null}
 */
export function getUser() {
  const userStr = localStorage.getItem(USER_KEY)
  if (!userStr) return null
  try {
    return JSON.parse(userStr)
  } catch {
    return null
  }
}

/**
 * 清除登录状态
 */
export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * 检查是否已登录
 * @returns {boolean}
 */
export function isAuthenticated() {
  return !!getToken()
}

/**
 * 获取认证请求头
 * @returns {object}
 */
export function getAuthHeaders() {
  const token = getToken()
  if (!token) return {}
  return {
    'Authorization': `Bearer ${token}`
  }
}

/**
 * 用户注册
 * @param {object} data - { username, password, email?, nickname? }
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export async function register(data) {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || ''
    const response = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    
    const result = await response.json()
    
    if (response.ok) {
      setAuth(result.access_token, result.user)
      return { success: true, data: result }
    } else {
      return { success: false, error: result.detail || '注册失败' }
    }
  } catch (error) {
    return { success: false, error: '网络错误，请稍后重试' }
  }
}

/**
 * 用户登录
 * @param {object} data - { username, password }
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export async function login(data) {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || ''
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    
    const result = await response.json()
    
    if (response.ok) {
      setAuth(result.access_token, result.user)
      return { success: true, data: result }
    } else {
      return { success: false, error: result.detail || '用户名或密码错误' }
    }
  } catch (error) {
    return { success: false, error: '网络错误，请稍后重试' }
  }
}

/**
 * 用户登出
 */
export async function logout() {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || ''
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }
    })
  } finally {
    clearAuth()
    window.location.href = '/login'
  }
}

/**
 * 获取当前用户信息
 * @returns {Promise<{ success: boolean, data?: object, error?: string }>}
 */
export async function getCurrentUser() {
  try {
    const API_BASE = import.meta.env.VITE_API_BASE || ''
    const response = await fetch(`${API_BASE}/auth/me`, {
      method: 'GET',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' }
    })
    
    if (response.ok) {
      const data = await response.json()
      return { success: true, data }
    } else if (response.status === 401) {
      clearAuth()
      return { success: false, error: '登录已过期' }
    } else {
      return { success: false, error: '获取用户信息失败' }
    }
  } catch (error) {
    return { success: false, error: '网络错误' }
  }
}
