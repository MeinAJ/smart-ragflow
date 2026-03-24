/**
 * API 工具函数
 * 处理 /v1/chat/completions 流式接口
 */

const API_BASE = '' // 使用 Vite 代理

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
 */
export async function streamChatCompletion(message, onChunk, onDone, onError, onDocs) {
  try {
    const response = await fetch(`${API_BASE}/v1/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        messages: [
          { role: 'user', content: message }
        ],
        stream: true
      })
    })

    if (!response.ok) {
      // 尝试读取后端返回的错误信息
      let errorMessage = getFriendlyHttpError(response.status)
      try {
        const errorData = await response.json()
        if (errorData && (errorData.message || errorData.error || errorData.detail)) {
          errorMessage = errorData.message || errorData.error || errorData.detail
        }
      } catch (e) {
        // 无法解析 JSON，使用默认友好提示
      }
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

      // 解码数据
      buffer += decoder.decode(value, { stream: true })
      
      // 处理 SSE 行（可能包含多个事件）
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // 保留未完成的行
      
      let currentEvent = null
      
      for (const line of lines) {
        const trimmedLine = line.trim()
        if (!trimmedLine) {
          // 空行表示事件结束
          currentEvent = null
          continue
        }
        
        // 解析事件类型
        if (trimmedLine.startsWith('event: ')) {
          currentEvent = trimmedLine.slice(7)
          continue
        }
        
        // 解析数据
        if (trimmedLine.startsWith('data: ')) {
          const data = trimmedLine.slice(6)
          
          // 检查结束标记
          if (data === '[DONE]') {
            onDone && onDone()
            return
          }
          
          // 处理特殊事件
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
          
          // 处理错误事件
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
          
          // 处理标准 OpenAI SSE 消息
          try {
            const json = JSON.parse(data)
            const content = json.choices?.[0]?.delta?.content
            if (content) {
              onChunk && onChunk(content)
            }
          } catch (e) {
            // 忽略解析错误
          }
        }
      }
    }
    
    // 处理剩余缓冲区
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
            } catch (e) {
              // 忽略
            }
          }
        }
      }
    }
  } catch (error) {
    console.error('Stream error:', error)
    // 提供更友好的网络错误提示
    let friendlyMessage = error.message || '请求失败'
    
    if (error.name === 'TypeError' && error.message.includes('fetch')) {
      friendlyMessage = '网络连接失败，请检查网络或稍后重试'
    } else if (error.name === 'AbortError') {
      friendlyMessage = '请求已取消'
    } else if (!friendlyMessage.includes('请') && !friendlyMessage.includes('请')) {
      // 如果错误信息不包含友好提示，添加通用提示
      friendlyMessage = '服务异常，请稍后再试'
    }
    
    onError && onError(friendlyMessage)
  }
}
