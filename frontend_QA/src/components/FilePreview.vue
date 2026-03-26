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

          <!-- Markdown / TXT / 代码 预览 -->
          <div v-else-if="isTextFile" class="text-preview" :class="{ 'code-file': isCode }">
            <div class="file-type-badge" v-if="isCode">{{ fileExtension.toUpperCase() }}</div>
            <div class="markdown-body" :class="{ 'code-content': isCode }" v-html="renderedContent"></div>
          </div>

          <!-- PDF 预览 -->
          <div v-else-if="isPdf" class="pdf-preview">
            <!-- 尝试使用浏览器内置 PDF 查看器 -->
            <iframe 
              v-if="!pdfError"
              :src="pdfViewerUrl" 
              frameborder="0" 
              width="100%" 
              height="100%"
              @error="handlePdfError"
              @load="pdfLoadTimeout && clearTimeout(pdfLoadTimeout); pdfLoadTimeout = null"
            ></iframe>
            <!-- 备用方案：使用 Google Docs Viewer -->
            <iframe 
              v-else-if="useGoogleViewer"
              :src="googlePdfViewerUrl" 
              frameborder="0" 
              width="100%" 
              height="100%"
            ></iframe>
            <!-- 如果都失败，显示下载选项 -->
            <div v-else class="pdf-fallback">
              <div class="fallback-icon">📄</div>
              <p>PDF 预览加载失败</p>
              <p class="fallback-hint">可能是跨域限制或文件较大导致</p>
              <div class="fallback-actions">
                <a :href="fileUrl" target="_blank" class="fallback-btn primary">
                  在新标签页打开
                </a>
                <a :href="fileUrl" download class="fallback-btn">
                  下载文件
                </a>
              </div>
            </div>
          </div>

          <!-- Office 文档预览（使用微软在线服务） -->
          <div v-else-if="isOffice" class="office-preview">
            <iframe :src="officeViewerUrl" frameborder="0" width="100%" height="100%"></iframe>
          </div>

          <!-- 图片预览 -->
          <div v-else-if="isImage" class="image-preview">
            <img :src="fileUrl" alt="预览图片" @load="loading = false" />
          </div>

          <!-- 视频预览 -->
          <div v-else-if="isVideo" class="video-preview">
            <video :src="fileUrl" controls preload="metadata" @loadedmetadata="loading = false">
              您的浏览器不支持视频预览
            </video>
          </div>

          <!-- 音频预览 -->
          <div v-else-if="isAudio" class="audio-preview">
            <div class="audio-icon">🎵</div>
            <p class="audio-name">{{ fileName }}</p>
            <audio :src="fileUrl" controls preload="metadata" @loadedmetadata="loading = false">
              您的浏览器不支持音频预览
            </audio>
          </div>

          <!-- 不支持的格式 -->
          <div v-else class="unsupported-state">
            <div class="unsupported-icon">{{ isArchive ? '📦' : isEbook ? '📚' : '📄' }}</div>
            <p>{{ isArchive ? '压缩文件' : isEbook ? '电子书文件' : '该文件格式' }}暂不支持在线预览</p>
            <p class="debug-info">文件名: {{ fileName }}<br>扩展名: {{ fileExtension }}</p>
            <div class="unsupported-actions">
              <a :href="fileUrl" target="_blank" class="download-btn primary">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="7 10 12 15 17 10"></polyline>
                  <line x1="12" y1="15" x2="12" y2="3"></line>
                </svg>
                点击下载
              </a>
              <a :href="fileUrl" target="_blank" class="download-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                  <polyline points="15 3 21 3 21 9"></polyline>
                  <line x1="10" y1="14" x2="21" y2="3"></line>
                </svg>
                新窗口打开
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// 配置 marked（确保每次都能正确渲染）
marked.setOptions({
  breaks: true,
  gfm: true
})

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
const pdfError = ref(false)
const useGoogleViewer = ref(false)
const pdfLoadTimeout = ref(null)

// 从字符串中提取扩展名
const extractExtension = (str) => {
  if (!str) return ''
  // 移除 URL 参数
  const withoutParams = str.split('?')[0]
  // 提取扩展名
  const match = withoutParams.match(/\.([a-zA-Z0-9]+)$/)
  return match ? match[1].toLowerCase() : ''
}

// 从 URL 中提取文件名
const extractFileNameFromUrl = (url) => {
  if (!url) return ''
  try {
    const urlObj = new URL(url)
    const pathParts = urlObj.pathname.split('/')
    return pathParts[pathParts.length - 1] || ''
  } catch (e) {
    // URL 解析失败，使用原始字符串
    const parts = url.split('/')
    return parts[parts.length - 1] || ''
  }
}

// 文件扩展名（改进逻辑，处理各种情况）
const fileExtension = computed(() => {
  // 首先尝试从 fileName 提取
  let ext = extractExtension(props.fileName)
  
  // 如果 fileName 没有扩展名，尝试从 URL 提取
  if (!ext && props.fileUrl) {
    const urlFileName = extractFileNameFromUrl(props.fileUrl)
    ext = extractExtension(urlFileName)
  }
  
  console.log('[FilePreview] File info:', { 
    fileName: props.fileName, 
    fileUrl: props.fileUrl, 
    extractedExt: ext 
  })
  
  return ext
})

// 文件类型判断 - 按类别分组管理
const TEXT_EXTENSIONS = ['md', 'markdown', 'txt', 'text', 'json', 'xml', 'yaml', 'yml', 'csv', 'log', 'ini', 'conf', 'config']
const CODE_EXTENSIONS = ['js', 'ts', 'jsx', 'tsx', 'vue', 'py', 'java', 'c', 'cpp', 'h', 'hpp', 'cs', 'go', 'rs', 'rb', 'php', 'swift', 'kt', 'scala', 'r', 'm', 'mm', 'sh', 'bash', 'zsh', 'fish', 'ps1', 'bat', 'cmd', 'sql', 'css', 'scss', 'sass', 'less', 'html', 'htm', 'htmx', 'jsp', 'asp', 'aspx', 'erl', 'ex', 'exs', 'clj', 'cljs', 'fs', 'fsx', 'hs', 'lhs', 'lua', 'pl', 'pm', 't', 'rkt', 'scm', 'ss', 'tsv', 'dart', 'groovy', 'gradle', 'dockerfile', 'makefile', 'cmake', 'vim', 'eml', 'vbs', 'applescript']
const PDF_EXTENSIONS = ['pdf']
const OFFICE_EXTENSIONS = ['doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx']
const IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg', 'ico', 'tiff', 'tif']
const VIDEO_EXTENSIONS = ['mp4', 'webm', 'ogg', 'ogv', 'mov', 'mkv', 'avi', 'flv', 'wmv', 'm4v', '3gp']
const AUDIO_EXTENSIONS = ['mp3', 'wav', 'ogg', 'oga', 'm4a', 'aac', 'flac', 'wma', 'opus', 'weba']
const ARCHIVE_EXTENSIONS = ['zip', 'rar', '7z', 'tar', 'gz', 'bz2', 'xz', 'lz', 'lzma', 'cab', 'iso']
const DOCUMENT_EXTENSIONS = ['epub', 'mobi', 'azw', 'azw3', 'djvu', 'fb2', 'cbz', 'cbr']

const isMarkdown = computed(() => ['md', 'markdown'].includes(fileExtension.value))
const isText = computed(() => TEXT_EXTENSIONS.includes(fileExtension.value))
const isCode = computed(() => CODE_EXTENSIONS.includes(fileExtension.value))
const isTextFile = computed(() => {
  const isText = isMarkdown.value || isText.value || isCode.value
  console.log('[FilePreview] isTextFile:', isText, 'ext:', fileExtension.value)
  return isText
})
const isPdf = computed(() => PDF_EXTENSIONS.includes(fileExtension.value))
const isOffice = computed(() => OFFICE_EXTENSIONS.includes(fileExtension.value))
const isImage = computed(() => IMAGE_EXTENSIONS.includes(fileExtension.value))
const isVideo = computed(() => VIDEO_EXTENSIONS.includes(fileExtension.value))
const isAudio = computed(() => AUDIO_EXTENSIONS.includes(fileExtension.value))
const isArchive = computed(() => ARCHIVE_EXTENSIONS.includes(fileExtension.value))
const isEbook = computed(() => DOCUMENT_EXTENSIONS.includes(fileExtension.value))

// 判断文件是否可以直接预览（不需要下载）
const isPreviewable = computed(() => isTextFile.value || isPdf.value || isOffice.value || isImage.value || isVideo.value || isAudio.value)

// 文件图标
const fileIcon = computed(() => {
  if (isMarkdown.value) return '📝'
  if (isCode.value) return '💻'
  if (isText.value) return '📄'
  if (isPdf.value) return '📕'
  if (['doc', 'docx'].includes(fileExtension.value)) return '📘'
  if (['xls', 'xlsx'].includes(fileExtension.value)) return '📊'
  if (['ppt', 'pptx'].includes(fileExtension.value)) return '📽️'
  if (isImage.value) return '🖼️'
  if (isVideo.value) return '🎬'
  if (isAudio.value) return '🎵'
  if (isArchive.value) return '📦'
  if (isEbook.value) return '📚'
  return '📎'
})

// PDF 预览 URL（使用浏览器内置查看器）
const pdfViewerUrl = computed(() => props.fileUrl)

// Google Docs PDF 查看器（备用方案）
const googlePdfViewerUrl = computed(() => {
  const encodedUrl = encodeURIComponent(props.fileUrl)
  return `https://docs.google.com/gview?embedded=1&url=${encodedUrl}`
})

// 处理 PDF 加载错误
const handlePdfError = () => {
  console.log('[FilePreview] PDF iframe error, trying Google Viewer...')
  pdfError.value = true
  useGoogleViewer.value = true
}

// Office 文档预览 URL
const officeViewerUrl = computed(() => {
  const encodedUrl = encodeURIComponent(props.fileUrl)
  return `https://view.officeapps.live.com/op/embed.aspx?src=${encodedUrl}`
})

// 渲染后的内容
const renderedContent = ref('<p style="color: #999;">正在加载...</p>')

// 获取代码文件的语言标识（用于语法高亮）
const getCodeLanguage = (ext) => {
  const langMap = {
    'js': 'javascript', 'ts': 'typescript', 'jsx': 'javascript', 'tsx': 'typescript',
    'vue': 'xml', 'py': 'python', 'java': 'java', 'c': 'c', 'cpp': 'cpp', 'h': 'c', 'hpp': 'cpp',
    'cs': 'csharp', 'go': 'go', 'rs': 'rust', 'rb': 'ruby', 'php': 'php',
    'swift': 'swift', 'kt': 'kotlin', 'scala': 'scala', 'r': 'r',
    'sh': 'bash', 'bash': 'bash', 'zsh': 'bash', 'fish': 'bash', 'ps1': 'powershell',
    'sql': 'sql', 'css': 'css', 'scss': 'scss', 'sass': 'scss', 'less': 'less',
    'html': 'xml', 'htm': 'xml', 'xml': 'xml', 'json': 'json', 'yaml': 'yaml', 'yml': 'yaml',
    'dockerfile': 'dockerfile', 'cmake': 'cmake', 'vim': 'vim', 'vb': 'vbnet',
    'vbs': 'vbscript', 'erl': 'erlang', 'ex': 'elixir', 'exs': 'elixir',
    'clj': 'clojure', 'cljs': 'clojure', 'fs': 'fsharp', 'fsx': 'fsharp',
    'hs': 'haskell', 'lhs': 'haskell', 'lua': 'lua', 'pl': 'perl', 'pm': 'perl',
    'rkt': 'scheme', 'scm': 'scheme', 'ss': 'scheme', 'dart': 'dart',
    'groovy': 'groovy', 'gradle': 'groovy', 'makefile': 'makefile',
    'csv': 'plaintext', 'tsv': 'plaintext', 'txt': 'plaintext', 'log': 'plaintext',
    'ini': 'ini', 'conf': 'ini', 'config': 'ini'
  }
  return langMap[ext] || 'plaintext'
}

// 渲染 Markdown 或纯文本/代码
const renderContent = async (content) => {
  if (!content) {
    renderedContent.value = '<p style="color: #999;">文件内容为空</p>'
    return
  }
  
  // 限制显示内容大小（避免大文件导致卡顿）
  const maxLength = 100000 // 最大显示 100KB
  const displayContent = content.length > maxLength 
    ? content.substring(0, maxLength) + '\n\n... (文件过大，仅显示前 ' + maxLength + ' 字符)'
    : content
  
  try {
    if (isMarkdown.value) {
      // marked 可能是异步的，使用 await
      const html = await marked.parse(displayContent)
      renderedContent.value = html
    } else if (isCode.value) {
      // 代码文件 - 使用 highlight.js 进行语法高亮
      const lang = getCodeLanguage(fileExtension.value)
      let highlightedCode
      try {
        // 尝试使用指定语言高亮
        if (hljs.getLanguage(lang)) {
          highlightedCode = hljs.highlight(displayContent, { language: lang, ignoreIllegals: true }).value
        } else {
          // 语言不存在时使用自动检测
          highlightedCode = hljs.highlightAuto(displayContent).value
        }
      } catch (e) {
        console.warn('[FilePreview] Highlight failed, using auto detect:', e)
        // 失败时使用自动检测
        highlightedCode = hljs.highlightAuto(displayContent).value
      }
      renderedContent.value = `<pre class="code-preview"><code class="hljs language-${lang}">${highlightedCode}</code></pre>`
    } else {
      // 纯文本，转义 HTML 并保留换行
      renderedContent.value = displayContent
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/\n/g, '<br>')
    }
  } catch (err) {
    console.error('[FilePreview] Render error:', err)
    // 渲染失败时显示纯文本
    renderedContent.value = displayContent
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
}

// 加载文本文件
const loadTextFile = async () => {
  if (!props.fileUrl) {
    error.value = '文件 URL 为空'
    return
  }
  
  loading.value = true
  error.value = ''
  fileContent.value = ''
  renderedContent.value = '<p style="color: #999;">正在加载...</p>'
  
  console.log('[FilePreview] Loading text file:', { 
    url: props.fileUrl, 
    fileName: props.fileName,
    extension: fileExtension.value,
    isMarkdown: isMarkdown.value,
    isCode: isCode.value
  })
  
  try {
    const response = await fetch(props.fileUrl)
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    
    // 检查内容类型
    const contentType = response.headers.get('content-type') || ''
    console.log('[FilePreview] Response content-type:', contentType)
    
    fileContent.value = await response.text()
    console.log('[FilePreview] File loaded successfully, size:', fileContent.value.length)
    
    if (fileContent.value.length === 0) {
      renderedContent.value = '<p style="color: #999;">文件内容为空</p>'
    } else {
      // 渲染内容
      await renderContent(fileContent.value)
    }
    
  } catch (err) {
    console.error('[FilePreview] Failed to load file:', err)
    
    // 处理 CORS 错误
    if (err.name === 'TypeError' && err.message.includes('fetch')) {
      error.value = '无法加载文件：跨域访问限制 (CORS) 或网络错误。请尝试点击右上角按钮在新窗口打开。'
    } else if (err.name === 'TypeError') {
      error.value = '无法加载文件：网络错误。请检查文件链接是否有效。'
    } else {
      error.value = '文件加载失败：' + (err.message || '未知错误')
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

// 打开预览的核心逻辑
const openPreview = async () => {
  console.log('[FilePreview] Opening preview:', { 
    fileName: props.fileName, 
    fileUrl: props.fileUrl,
    extension: fileExtension.value,
    isText: isTextFile.value,
    isPdf: isPdf.value,
    isOffice: isOffice.value,
    isImage: isImage.value,
    isVideo: isVideo.value,
    isAudio: isAudio.value
  })
  
  // 重置状态
  error.value = ''
  fileContent.value = ''
  renderedContent.value = '<p style="color: #999;">正在加载...</p>'
  pdfError.value = false
  useGoogleViewer.value = false
  
  // 清除之前的超时
  if (pdfLoadTimeout.value) {
    clearTimeout(pdfLoadTimeout.value)
    pdfLoadTimeout.value = null
  }
  
  if (isTextFile.value) {
    console.log('[FilePreview] Loading text/code file...')
    await loadTextFile()
  } else if (isOffice.value || isPdf.value) {
    loading.value = true
    setTimeout(() => {
      loading.value = false
    }, 1000)
    
    // PDF 加载超时检测（5秒后如果仍显示空白，则尝试备用方案）
    if (isPdf.value) {
      pdfLoadTimeout.value = setTimeout(() => {
        console.log('[FilePreview] PDF load timeout, showing fallback options')
        pdfError.value = true
      }, 5000)
    }
  } else if (isImage.value || isVideo.value || isAudio.value) {
    // 这些类型直接通过标签加载，不需要额外处理
    loading.value = true
    // 3秒后自动隐藏 loading（因为媒体加载事件可能不可靠）
    setTimeout(() => {
      loading.value = false
    }, 500)
  } else {
    loading.value = false
  }
  
  // 添加键盘事件
  document.addEventListener('keydown', handleKeydown)
  document.body.style.overflow = 'hidden'
}

// 关闭预览
const closePreview = () => {
  document.removeEventListener('keydown', handleKeydown)
  document.body.style.overflow = ''
  // 清除超时
  if (pdfLoadTimeout.value) {
    clearTimeout(pdfLoadTimeout.value)
    pdfLoadTimeout.value = null
  }
}

// 监听可见性变化
watch(() => props.visible, (newVal) => {
  if (newVal) {
    openPreview()
  } else {
    closePreview()
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

.text-preview.code-file {
  padding: 16px;
  background: #1e1e1e;
}

.file-type-badge {
  display: inline-block;
  padding: 4px 12px;
  background: #667eea;
  color: white;
  font-size: 12px;
  font-weight: 600;
  border-radius: 4px;
  margin-bottom: 12px;
}

.code-content pre.code-preview {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 20px;
  overflow-x: auto;
  margin: 0;
}

.code-content pre.code-preview code {
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: #d4d4d4;
}

/* 代码高亮适配深色背景 */
.code-content .hljs {
  background: transparent;
  padding: 0;
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

/* PDF 加载失败备用显示 */
.pdf-fallback {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  background: #f8f9fa;
  text-align: center;
  padding: 40px;
}

.fallback-icon {
  font-size: 64px;
  margin-bottom: 20px;
}

.pdf-fallback p {
  font-size: 18px;
  color: #333;
  margin: 8px 0;
}

.fallback-hint {
  font-size: 14px !important;
  color: #999 !important;
}

.fallback-actions {
  display: flex;
  gap: 16px;
  margin-top: 24px;
}

.fallback-btn {
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  transition: all 0.2s;
  border: 1px solid #ddd;
  background: white;
  color: #666;
  cursor: pointer;
}

.fallback-btn:hover {
  background: #f0f0f0;
}

.fallback-btn.primary {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.fallback-btn.primary:hover {
  background: #5a6fd6;
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

/* 视频预览 */
.video-preview {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  height: 100%;
  background: #1a1a1a;
}

.video-preview video {
  max-width: 100%;
  max-height: 100%;
  border-radius: 8px;
}

/* 音频预览 */
.audio-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  height: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  text-align: center;
}

.audio-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.audio-name {
  font-size: 18px;
  font-weight: 500;
  margin-bottom: 24px;
  max-width: 80%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.audio-preview audio {
  width: 80%;
  max-width: 500px;
}

.audio-preview audio::-webkit-media-controls-panel {
  background: white;
}

/* 不支持格式的下载按钮 */
.unsupported-actions {
  display: flex;
  gap: 16px;
  margin-top: 24px;
  flex-wrap: wrap;
  justify-content: center;
}

.download-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  font-weight: 500;
  transition: all 0.2s;
  border: 1px solid #ddd;
  background: white;
  color: #666;
  cursor: pointer;
}

.download-btn:hover {
  background: #f5f5f5;
  transform: translateY(-1px);
}

.download-btn.primary {
  background: #667eea;
  color: white;
  border-color: #667eea;
}

.download-btn.primary:hover {
  background: #5a6fd6;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.download-btn svg {
  width: 18px;
  height: 18px;
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
