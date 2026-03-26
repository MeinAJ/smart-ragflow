<template>
  <div :class="['message', role]">
    <div class="avatar">
      {{ role === 'user' ? '👤' : '🤖' }}
    </div>
    <div class="content">
      <div class="role-label">{{ role === 'user' ? '用户' : '助手' }}</div>
      <div class="markdown-body" v-html="renderedContent" ref="contentRef"></div>
      <div v-if="isStreaming" class="streaming-indicator">
        <span class="dot"></span>
        <span class="dot"></span>
        <span class="dot"></span>
      </div>
    </div>
  </div>

  <!-- 文件预览弹窗 -->
  <FilePreview
    v-model:visible="previewVisible"
    :file-url="previewFile.url"
    :file-name="previewFile.name"
  />
</template>

<script setup>
import { computed, ref, watch, onUpdated, nextTick } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'
import FilePreview from './FilePreview.vue'

const props = defineProps({
  role: {
    type: String,
    default: 'assistant'
  },
  content: {
    type: String,
    default: ''
  },
  isStreaming: {
    type: Boolean,
    default: false
  },
  // 引用文档元数据，用于显示 tooltip
  contextDocs: {
    type: Array,
    default: () => []
  }
})

const contentRef = ref(null)
const previewVisible = ref(false)
const previewFile = ref({ url: '', name: '' })

// 配置 marked（异步模式避免阻塞）
marked.setOptions({
  highlight: function(code, lang) {
    if (lang && hljs.getLanguage(lang)) {
      return hljs.highlight(code, { language: lang }).value
    }
    return hljs.highlightAuto(code).value
  },
  breaks: true,
  gfm: true
})

// 自定义 renderer 处理引用链接
const renderer = new marked.Renderer()
renderer.link = function(href, title, text) {
  // 检查是否是引用链接 [引用N]
  const citeMatch = text.match(/^引用(\d+)$/)
  if (citeMatch) {
    const docIndex = parseInt(citeMatch[1]) - 1
    const doc = props.contextDocs[docIndex]
    
    // 调试日志
    console.log('[ChatMessage] Rendering cite link:', { docIndex, doc })
    
    const docTitle = doc ? (doc.title || doc.metadata?.title || `文档 ${citeMatch[1]}`) : `文档 ${citeMatch[1]}`
    // 获取原始文件名（用于识别文件类型）- 优先使用 file_name 字段
    const fileName = doc ? (doc.file_name || doc.metadata?.file_name || doc.title || '') : ''
    // 获取 doc_id 用于后端下载 - 优先使用 doc_id 字段
    const docId = doc ? (doc.doc_id || doc.metadata?.doc_id || '') : ''
    
    console.log('[ChatMessage] Cite link data:', { docTitle, fileName, docId })
    
    // 添加 data-preview 属性标识这是一个可预览的链接
    return `<a href="${href}" class="cite-link" data-preview="true" data-doc-title="${docTitle}" data-file-name="${fileName}" data-doc-id="${docId}" title="点击预览：${docTitle}">[引用${citeMatch[1]}]</a>`
  }
  // 普通链接
  return `<a href="${href}" title="${title || ''}" target="_blank" rel="noopener noreferrer">${text}</a>`
}

// 使用 ref 存储渲染内容，配合 watch 实现更细粒度的控制
const renderedContent = ref('')

// 实时监听 content 和 contextDocs 变化并更新渲染
watch(
  [() => props.content, () => props.contextDocs],
  ([newContent, newContextDocs]) => {
    console.log('[ChatMessage] Content or contextDocs changed:', { 
      contentLength: newContent?.length, 
      docsCount: newContextDocs?.length 
    })
    
    if (!newContent) {
      renderedContent.value = ''
      return
    }
    // 使用 requestAnimationFrame 避免阻塞主线程
    requestAnimationFrame(() => {
      renderedContent.value = marked(newContent, { renderer })
      // 渲染完成后绑定点击事件
      nextTick(() => {
        bindCiteLinkEvents()
      })
    })
  },
  { immediate: true, flush: 'post' }
)

// 引用链接点击处理 - 使用事件委托
const handleCiteClick = (e) => {
  // 查找最近的 .cite-link 元素
  const link = e.target.closest('.cite-link[data-preview="true"]')
  if (!link) return
  
  e.preventDefault()
  e.stopPropagation()
  
  const href = link.getAttribute('href')
  const title = link.getAttribute('data-doc-title') || '未命名文档'
  // 优先使用原始文件名（包含扩展名），如果没有则使用文档标题
  const fileName = link.getAttribute('data-file-name') || title
  // 获取 doc_id 用于后端下载
  const docId = link.getAttribute('data-doc-id')
  
  console.log('[ChatMessage] Cite link clicked:', { href, title, fileName, docId })
  
  if (docId && docId.trim() !== '') {
    // 使用后端下载端点，避免跨域问题
    const downloadUrl = `/files/download/${docId}`
    previewFile.value = { url: downloadUrl, name: fileName }
    previewVisible.value = true
    console.log('[ChatMessage] Opening preview with docId:', { url: downloadUrl, name: fileName, originalUrl: href })
  } else if (href && href !== 'null' && href !== 'undefined') {
    // 兼容旧数据：直接使用原始 URL
    previewFile.value = { url: href, name: fileName }
    previewVisible.value = true
    console.log('[ChatMessage] Opening preview (fallback):', { url: href, name: fileName })
  } else {
    console.error('[ChatMessage] Cannot preview: no valid docId or href', { href, docId })
    alert('无法预览该文件：缺少文件信息')
  }
}

// 绑定引用链接点击事件 - 使用事件委托
const bindCiteLinkEvents = () => {
  if (!contentRef.value) return
  
  // 使用事件委托，直接绑定到容器元素
  contentRef.value.removeEventListener('click', handleCiteClick)
  contentRef.value.addEventListener('click', handleCiteClick)
  
  const citeLinks = contentRef.value.querySelectorAll('.cite-link[data-preview="true"]')
  console.log('[ChatMessage] Bound click events to', citeLinks.length, 'cite links')
}

// 渲染完成后绑定事件
onUpdated(() => {
  bindCiteLinkEvents()
})
</script>

<style scoped>
.message {
  display: flex;
  gap: 12px;
  padding: 16px 20px;
  margin-bottom: 8px;
  border-radius: 12px;
  animation: fadeIn 0.3s ease;
  max-width: 100%;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message.user {
  background-color: rgba(102, 126, 234, 0.1);
  flex-direction: row-reverse;
}

.message.user .content {
  align-items: flex-end;
}

.message.assistant {
  background-color: rgba(255, 255, 255, 0.05);
}

.message.user .role-label {
  text-align: right;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.content {
  flex: 1;
  min-width: 0;
}

.role-label {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 4px;
  font-weight: 500;
}

.message.user .role-label {
  color: rgba(102, 126, 234, 0.8);
}

:deep(.markdown-body) {
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.9);
}

:deep(.markdown-body p) {
  margin: 0 0 12px 0;
}

:deep(.markdown-body p:last-child) {
  margin-bottom: 0;
}

:deep(.markdown-body pre) {
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  padding: 12px;
  overflow-x: auto;
  margin: 8px 0;
}

:deep(.markdown-body code) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
}

:deep(.markdown-body pre code) {
  background: none;
  padding: 0;
}

:deep(.markdown-body :not(pre) > code) {
  background: rgba(255, 255, 255, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
  color: #ff7eb6;
}

:deep(.markdown-body h1,
.markdown-body h2,
.markdown-body h3,
.markdown-body h4) {
  margin: 16px 0 12px 0;
  font-weight: 600;
}

:deep(.markdown-body ul,
.markdown-body ol) {
  margin: 8px 0;
  padding-left: 24px;
}

:deep(.markdown-body li) {
  margin: 4px 0;
}

:deep(.markdown-body blockquote) {
  border-left: 4px solid rgba(102, 126, 234, 0.5);
  padding-left: 16px;
  margin: 8px 0;
  color: rgba(255, 255, 255, 0.6);
}

:deep(.markdown-body table) {
  border-collapse: collapse;
  width: 100%;
  margin: 12px 0;
}

:deep(.markdown-body th,
.markdown-body td) {
  border: 1px solid rgba(255, 255, 255, 0.1);
  padding: 8px 12px;
  text-align: left;
}

:deep(.markdown-body th) {
  background: rgba(255, 255, 255, 0.1);
  font-weight: 600;
}

/* 引用链接样式 */
:deep(.cite-link) {
  display: inline-block;
  background: #667eea;
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
  text-decoration: none;
  margin: 0 2px;
  transition: all 0.2s ease;
  cursor: pointer;
}

:deep(.cite-link:hover) {
  background: #5a6fd6;
  transform: translateY(-1px);
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.3);
}

/* 连续引用链接的间距 */
:deep(.cite-link + .cite-link) {
  margin-left: 0;
}

.streaming-indicator {
  display: flex;
  gap: 4px;
  margin-top: 8px;
  align-items: center;
}

.dot {
  width: 6px;
  height: 6px;
  background: #667eea;
  border-radius: 50%;
  animation: bounce 1.4s infinite ease-in-out;
}

.dot:nth-child(1) {
  animation-delay: -0.32s;
}

.dot:nth-child(2) {
  animation-delay: -0.16s;
}

@keyframes bounce {
  0%, 80%, 100% {
    transform: scale(0);
  }
  40% {
    transform: scale(1);
  }
}
</style>
