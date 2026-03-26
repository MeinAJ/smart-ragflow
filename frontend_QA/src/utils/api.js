/**
 * API 工具函数
 * 处理 /v1/chat/completions 流式接口
 */

import { getAuthHeaders, getToken } from './auth.js'

// API 基础地址
const API_BASE = import.meta.env.VITE_API_BASE || ''

/**
 * 获取友好的 HTTP 错误信息
 * @param {number} status - HTTP 状态码
 * @returns {string} 友好的错误提示
 */
function getFriendlyHttpError(status) {
  const errorMessages = {
    400: '请求参数错误，请检查输入内容',
    401: '未授权访问，请重新登录',
    403: '没有权限访问该服务',
    404: '服务接口不存在',
    429: '请求过于频繁，请稍后再试',
    500: '服务器内部错误，请稍后再试',
    502: '服务暂时不可用，请稍后再试',
    503: '服务正在维护中，请稍后再试',
    504: '服务响应超时，请稍后再试'
  }
  return errorMessages[status] || `服务异常 (${status})，请稍后再试`
}

/**
 * 流式调用 chat completions 接口
 * @param {string} message - 用户输入
 * @param {function} onChunk - 接收流式数据的回调
 * @param {function} onDone - 完成回调
 * @param {function} onError - 错误回调
 * @param {function} onDocs - 接收检索文档元数据的回调 (docs) => {}
 * @param {string} sessionId - 会话ID，用于关联历史对话
 */
export async function streamChatCompletion(message, onChunk, onDone, onError, onDocs, sessionId = null) {
  try {
    const requestBody = {
      messages: [
        { role: 'user', content: message }
      ],
      stream: true
    }
    
    if (sessionId) {
      requestBody.session_id = sessionId
    }
    
    const response = await fetch(`${API_BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify(requestBody)
    })

    if (response.status === 401) {
      // Token 过期，跳转到登录页
      onError('登录已过期，请重新登录')
      setTimeout(() => {
        window.location.href = '/login'
      }, 1500)
      return
    }

    if (!response.ok) {
      let errorMessage = getFriendlyHttpError(response.status)
      try {
        const errorData = await response.json()
        if (errorData && (errorData.message || errorData.error || errorData.detail)) {
          errorMessage = errorData.message || errorData.error || errorData.detail
        }
      } catch (e) {}
      throw new Error(errorMessage)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        onDone && onDone()
        break
      }

      buffer += decoder.decode(value, { stream: true })
      
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      
      let currentEvent = null
      
      for (const line of lines) {
        const trimmedLine = line.trim()
        if (!trimmedLine) {
          currentEvent = null
          continue
        }
        
        if (trimmedLine.startsWith('event: ')) {
          currentEvent = trimmedLine.slice(7)
          continue
        }
        
        if (trimmedLine.startsWith('data: ')) {
          const data = trimmedLine.slice(6)
          
          if (data === '[DONE]') {
            onDone && onDone()
            return
          }
          
          if (currentEvent === 'context_docs') {
            try {
              const json = JSON.parse(data)
              if (json.docs && onDocs) {
                onDocs(json.docs)
              }
            } catch (e) {
              console.warn('Failed to parse context docs:', e)
            }
            continue
          }
          
          if (currentEvent === 'error') {
            try {
              const json = JSON.parse(data)
              const errorMsg = json.message || '服务出现异常'
              onError && onError(errorMsg)
            } catch (e) {
              onError && onError(data)
            }
            return
          }
          
          try {
            const json = JSON.parse(data)
            const content = json.choices?.[0]?.delta?.content
            if (content) {
              onChunk && onChunk(content)
            }
          } catch (e) {}
        }
      }
    }
    
    if (buffer.trim()) {
      const lines = buffer.split('\n')
      for (const line of lines) {
        const trimmedLine = line.trim()
        if (trimmedLine.startsWith('data: ')) {
          const data = trimmedLine.slice(6)
          if (data === '[DONE]') {
            onDone && onDone()
          } else {
            try {
              const json = JSON.parse(data)
              const content = json.choices?.[0]?.delta?.content
              if (content) {
                onChunk && onChunk(content)
              }
            } catch (e) {}
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream error:', error)
    let friendlyMessage = error.message || '请求失败'
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      friendlyMessage = '无法连接到后端服务，请确认服务已启动'
    } else if (!friendlyMessage.includes('请') && !friendlyMessage.includes('登录')) {
      friendlyMessage = '服务异常，请稍后再试'
    }
    
    onError && onError(friendlyMessage)
  }
}

/**
 * 健康检查 - 测试后端服务是否可用
 * @returns {Promise<{ok: boolean, message: string}>}
 */
export async function healthCheck() {
  try {
    const response = await fetch(`${API_BASE}/health`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' }
    })
    
    if (response.ok) {
      const data = await response.json()
      return { ok: true, message: `服务正常: ${data.status || 'ok'}` }
    } else {
      return { ok: false, message: `服务异常: HTTP ${response.status}` }
    }
  } catch (error) {
    return { 
      ok: false, 
      message: `连接失败: ${error.message}`
    }
  }
}

/**
 * 获取会话列表
 * @returns {Promise<Array<{session_id: string, message_count: number, last_active: string}>>}
 */
export async function getSessionList(limit = 50) {
  try {
    const response = await fetch(`${API_BASE}/history/sessions?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      }
    })
    
    if (response.ok) {
      return await response.json()
    } else if (response.status === 401) {
      window.location.href = '/login'
      return []
    } else {
      console.error('获取会话列表失败:', response.status)
      return []
    }
  } catch (error) {
    console.error('获取会话列表错误:', error)
    return []
  }
}

/**
 * 获取指定会话的消息历史
 * @param {string} sessionId - 会话ID
 * @param {number} limit - 获取消息数量
 * @returns {Promise<Array<{id: number, role: string, content: string, created_at: string}>>}
 */
export async function getSessionMessages(sessionId, limit = 20) {
  try {
    const response = await fetch(`${API_BASE}/history/sessions/${sessionId}/messages?limit=${limit}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      }
    })
    
    if (response.ok) {
      const data = await response.json()
      return data.messages || []
    } else if (response.status === 401) {
      window.location.href = '/login'
      return []
    } else {
      console.error('获取会话消息失败:', response.status)
      return []
    }
  } catch (error) {
    console.error('获取会话消息错误:', error)
    return []
  }
}

/**
 * 删除会话
 * @param {string} sessionId - 会话ID
 * @returns {Promise<boolean>}
 */
export async function deleteSession(sessionId) {
  try {
    const response = await fetch(`${API_BASE}/history/sessions/${sessionId}`, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      }
    })
    
    if (response.status === 401) {
      window.location.href = '/login'
      return false
    }
    
    return response.ok
  } catch (error) {
    console.error('删除会话错误:', error)
    return false
  }
}

/**
 * 更新会话名称
 * @param {string} sessionId - 会话ID
 * @param {string} sessionName - 新的会话名称
 * @returns {Promise<boolean>}
 */
export async function updateSessionName(sessionId, sessionName) {
  try {
    const response = await fetch(`${API_BASE}/history/sessions/${sessionId}/name`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ session_name: sessionName })
    })
    
    if (response.status === 401) {
      window.location.href = '/login'
      return false
    }
    
    return response.ok
  } catch (error) {
    console.error('更新会话名称错误:', error)
    return false
  }
}

/**
 * 置顶/取消置顶会话
 * @param {string} sessionId - 会话ID
 * @param {boolean} isPinned - 是否置顶
 * @returns {Promise<boolean>}
 */
export async function pinSession(sessionId, isPinned) {
  try {
    const response = await fetch(`${API_BASE}/history/sessions/${sessionId}/pin`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders()
      },
      body: JSON.stringify({ is_pinned: isPinned })
    })
    
    if (response.status === 401) {
      window.location.href = '/login'
      return false
    }
    
    return response.ok
  } catch (error) {
    console.error('置顶会话错误:', error)
    return false
  }
}
