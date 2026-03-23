<template>
  <Teleport to="body">
    <div v-if="visible" class="preview-overlay" @click.self="close">
      <div class="preview-container">
        <!-- 头部 -->
        <div class="preview-header">
          <div class="preview-title">
            <span class="file-icon">{{ fileIcon }}</span>
            <span class="file-name">{{ fileName || '未命名文件' }}</span>
            <span v-if="fileExtension" class="file-ext">({{ fileExtension }})</span>
          </div>
          <div class="preview-actions">
            <a :href="fileUrl" target="_blank" class="action-btn" title="在新窗口打开">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                <polyline points="15 3 21 3 21 9"></polyline>
                <line x1="10" y1="14" x2="21" y2="3"></line>
              </svg>
            </a>
            <button class="action-btn close-btn" @click="close" title="关闭">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        <!-- 内容区 -->
        <div class="preview-body">
          <!-- 加载中 -->
          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <p>正在加载文件...</p>
          </div>

          <!-- 错误提示 -->
          <div v-else-if="error" class="error-state">
            <div class="error-icon">⚠️</div>
            <p>{{ error }}</p>
            <a :href="fileUrl" target="_blank" class="download-link">点击下载文件查看</a>
          </div>

          <!-- Markdown / TXT 预览 -->
          <div v-else-if="isTextFile" class="text-preview">
            <div class="markdown-body" v-html="renderedContent"></div>
          </div>

          <!-- PDF 预览 -->
          <div v-else-if="isPdf" class="pdf-preview">
            <iframe :src="pdfViewerUrl" frameborder="0" width="100%" height="100%"></iframe>
          </div>

          <!-- Office 文档预览（使用微软在线服务） -->
          <div v-else-if="isOffice" class="office-preview">
            <iframe :src="officeViewerUrl" frameborder="0" width="100%" height="100%"></iframe>
          </div>

          <!-- 图片预览 -->
          <div v-else-if="isImage" class="image-preview">
            <img :src="fileUrl" alt="预览图片" @load="loading = false" />
          </div>

          <!-- 不支持的格式 -->
          <div v-else class="unsupported-state">
            <div class="unsupported-icon">📄</div>
            <p>该文件格式暂不支持在线预览</p>
            <p class="debug-info">文件名: {{ fileName }}<br>扩展名: {{ fileExtension }}</p>
            <a :href="fileUrl" target="_blank" class="download-link">点击下载文件</a>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  fileUrl: {
    type: String,
    default: ''
  },
  fileName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['update:visible', 'close'])

const loading = ref(false)
const error = ref('')
const fileContent = ref('')

// 文件扩展名（改进逻辑，处理各种情况）
const fileExtension = computed(() => {
  // 优先使用 fileName
  let name = props.fileName || ''
  
  // 如果 fileName 没有扩展名，尝试从 URL 提取
  if (!name.includes('.')) {
    // 从 URL 中提取文件名部分
    try {
      const url = new URL(props.fileUrl)
      const pathParts = url.pathname.split('/')
      name = pathParts[pathParts.length - 1] || ''
    } catch (e) {
      // URL 解析失败，使用原始字符串
      const parts = props.fileUrl.split('/')
      name = parts[parts.length - 1] || ''
    }
  }
  
  // 提取扩展名
  const match = name.match(/\.([a-zA-Z0-9]+)(?:\?.*)?$/)
  const ext = match ? match[1].toLowerCase() : ''
  
  console.log('[FilePreview] File info:', { 
    fileName: props.fileName, 
    fileUrl: props.fileUrl, 
    extractedExt: ext 
  })
  
  return ext
})

// 文件类型判断
const isMarkdown = computed(() => ['md', 'markdown'].includes(fileExtension.value))
const isText = computed(() => ['txt', 'text', 'json', 'xml', 'yaml', 'yml', 'csv', 'log'].includes(fileExtension.value))
const isTextFile = computed(() => {
  const isText = isMarkdown.value || isText.value
  console.log('[FilePreview] isTextFile:', isText, 'ext:', fileExtension.value)
  return isText
})
const isPdf = computed(() => fileExtension.value === 'pdf')
const isOffice = computed(() => ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx'].includes(fileExtension.value))
const isImage = computed(() => ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'].includes(fileExtension.value))

// 文件图标
const fileIcon = computed(() => {
  if (isMarkdown.value) return '📝'
  if (isText.value) return '📄'
  if (isPdf.value) return '📕'
  if (['doc', 'docx'].includes(fileExtension.value)) return '📘'
  if (['xls', 'xlsx'].includes(fileExtension.value)) return '📊'
  if (['ppt', 'pptx'].includes(fileExtension.value)) return '📽️'
  if (isImage.value) return '🖼️'
  return '📎'
})

// PDF 预览 URL
const pdfViewerUrl = computed(() => props.fileUrl)

// Office 文档预览 URL
const officeViewerUrl = computed(() => {
  const encodedUrl = encodeURIComponent(props.fileUrl)
  return `https://view.officeapps.live.com/op/embed.aspx?src=${encodedUrl}`
})

// 渲染 Markdown
const renderedContent = computed(() => {
  if (!fileContent.value) return '<p style="color: #999;">文件内容为空</p>'
  if (isMarkdown.value) {
    return marked(fileContent.value)
  }
  // 纯文本，转义 HTML 并保留换行
  return fileContent.value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\n/g, '<br>')
})

// 加载文本文件
const loadTextFile = async () => {
  if (!props.fileUrl) {
    error.value = '文件 URL 为空'
    return
  }
  
  loading.value = true
  error.value = ''
  fileContent.value = ''
  
  console.log('[FilePreview] Loading text file:', props.fileUrl)
  
  try {
    const response = await fetch(props.fileUrl)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    fileContent.value = await response.text()
    console.log('[FilePreview] File loaded, size:', fileContent.value.length)
  } catch (err) {
    console.error('[FilePreview] Failed to load file:', err)
    
    // 处理 CORS 错误
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      error.value = '无法加载文件：跨域访问限制 (CORS)。请尝试点击右上角按钮在新窗口打开。'
    } else {
      error.value = '文件加载失败：' + (err.message || '网络错误')
    }
  } finally {
    loading.value = false
  }
}

// 关闭弹窗
const close = () => {
  emit('update:visible', false)
  emit('close')
}

// 监听可见性变化
watch(() => props.visible, (newVal) => {
  console.log('[FilePreview] Visibility changed:', newVal, 'ext:', fileExtension.value)
  
  if (newVal) {
    // 重置状态
    error.value = ''
    fileContent.value = ''
    
    if (isTextFile.value) {
      console.log('[FilePreview] Loading text file...')
      loadTextFile()
    } else if (isOffice.value || isPdf.value) {
      loading.value = true
      setTimeout(() => {
        loading.value = false
      }, 1000)
    } else {
      loading.value = false
    }
    
    // 添加键盘事件
    document.addEventListener('keydown', handleKeydown)
    document.body.style.overflow = 'hidden'
  } else {
    document.removeEventListener('keydown', handleKeydown)
    document.body.style.overflow = ''
  }
})

// ESC 键关闭
const handleKeydown = (e) => {
  if (e.key === 'Escape') {
    close()
  }
}
</script>

<style scoped>
.preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 20px;
}

.preview-container {
  background: white;
  border-radius: 12px;
  width: 90%;
  height: 85%;
  max-width: 1200px;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #eee;
  background: #f8f9fa;
  flex-shrink: 0;
}

.preview-title {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 16px;
  font-weight: 500;
  color: #333;
  overflow: hidden;
}

.file-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.file-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-ext {
  color: #999;
  font-size: 14px;
  font-weight: normal;
}

.preview-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  border: none;
  background: white;
  color: #666;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
}

.action-btn:hover {
  background: #e8f0fe;
  color: #667eea;
}

.action-btn svg {
  width: 18px;
  height: 18px;
}

.close-btn:hover {
  background: #ffebee;
  color: #c62828;
}

.preview-body {
  flex: 1;
  overflow: auto;
  position: relative;
}

/* 加载状态 */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 3px solid #f3f3f3;
  border-top: 3px solid #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin-bottom: 16px;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* 错误状态 */
.error-state,
.unsupported-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #666;
  text-align: center;
  padding: 40px;
}

.error-icon,
.unsupported-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.debug-info {
  font-size: 12px;
  color: #999;
  margin: 16px 0;
  font-family: monospace;
}

.download-link {
  margin-top: 16px;
  padding: 10px 20px;
  background: #667eea;
  color: white;
  border-radius: 8px;
  text-decoration: none;
  transition: all 0.2s;
}

.download-link:hover {
  background: #5a6fd6;
}

/* 文本预览 */
.text-preview {
  padding: 32px;
  max-width: 900px;
  margin: 0 auto;
  min-height: 100%;
  background: white;
}

.markdown-body {
  line-height: 1.8;
  color: #333;
  font-size: 15px;
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin: 32px 0 16px;
  font-weight: 600;
  line-height: 1.4;
}

.markdown-body :deep(h1) { font-size: 28px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
.markdown-body :deep(h2) { font-size: 24px; border-bottom: 1px solid #eee; padding-bottom: 8px; }
.markdown-body :deep(h3) { font-size: 20px; }
.markdown-body :deep(h4) { font-size: 18px; }

.markdown-body :deep(p) {
  margin: 0 0 16px;
}

.markdown-body :deep(pre) {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  overflow-x: auto;
  margin: 16px 0;
}

.markdown-body :deep(code) {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.markdown-body :deep(:not(pre) > code) {
  background: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  color: #e83e8c;
  font-size: 14px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 16px 0;
  padding-left: 32px;
}

.markdown-body :deep(li) {
  margin: 8px 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid #667eea;
  padding-left: 16px;
  margin: 16px 0;
  color: #666;
  background: #f8f9fa;
  padding: 12px 16px;
  border-radius: 0 8px 8px 0;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 16px 0;
}

.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #ddd;
  padding: 12px;
  text-align: left;
}

.markdown-body :deep(th) {
  background: #f5f5f5;
  font-weight: 600;
}

.markdown-body :deep(tr:nth-child(even)) {
  background: #f9f9f9;
}

.markdown-body :deep(a) {
  color: #667eea;
  text-decoration: none;
}

.markdown-body :deep(a:hover) {
  text-decoration: underline;
}

.markdown-body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
}

.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid #eee;
  margin: 32px 0;
}

/* PDF 预览 */
.pdf-preview,
.office-preview {
  width: 100%;
  height: 100%;
}

.pdf-preview iframe,
.office-preview iframe {
  width: 100%;
  height: 100%;
  border: none;
}

/* 图片预览 */
.image-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  height: 100%;
  background: #f5f5f5;
}

.image-preview img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 响应式 */
@media (max-width: 768px) {
  .preview-container {
    width: 100%;
    height: 100%;
    max-width: none;
    border-radius: 0;
  }
  
  .preview-overlay {
    padding: 0;
  }
  
  .text-preview {
    padding: 20px;
  }
}
</style>
