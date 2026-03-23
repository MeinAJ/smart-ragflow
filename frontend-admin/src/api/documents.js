import axios from 'axios'

const API_BASE = '/api'

// 创建 axios 实例
const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 响应拦截器 - 统一错误处理
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    const message = error.response?.data?.detail || 
                   error.response?.data?.message || 
                   error.message || 
                   '请求失败'
    return Promise.reject(message)
  }
)

/**
 * 1. 获取文档列表
 * @param {Object} params - 查询参数
 * @param {number} params.page - 页码
 * @param {number} params.size - 每页数量
 * @param {string} params.keyword - 搜索关键词
 * @returns {Promise<{total: number, items: Array}>}
 */
export function getDocuments(params = {}) {
  return apiClient.get('/documents', { params })
}

/**
 * 2. 上传/创建文档
 * @param {File} file - 文件对象
 * @param {Object} metadata - 文档元数据
 * @returns {Promise<Object>}
 */
export function uploadDocument(file, metadata = {}) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('metadata', JSON.stringify(metadata))
  
  return apiClient.post('/documents', formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

/**
 * 3. 删除文档
 * @param {string} docId - 文档ID
 * @returns {Promise<Object>}
 */
export function deleteDocument(docId) {
  return apiClient.delete(`/documents/${docId}`)
}

/**
 * 4. 更新文档信息
 * @param {string} docId - 文档ID
 * @param {Object} data - 更新数据
 * @returns {Promise<Object>}
 */
export function updateDocument(docId, data) {
  return apiClient.put(`/documents/${docId}`, data)
}

/**
 * 5. 解析文档
 * @param {string} docId - 文档ID
 * @param {Object} options - 解析选项
 * @returns {Promise<Object>}
 */
export function parseDocument(docId, options = {}) {
  return apiClient.post(`/documents/${docId}/parse`, options)
}

/**
 * 获取文档解析状态
 * @param {string} docId - 文档ID
 * @returns {Promise<Object>}
 */
export function getDocumentStatus(docId) {
  return apiClient.get(`/documents/${docId}/status`)
}
