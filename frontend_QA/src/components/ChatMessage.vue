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
</template>

<script setup>
import { computed, ref, watch, onUpdated, nextTick } from 'vue'
import { marked } from 'marked'
import hljs from 'highlight.js'
import 'highlight.js/styles/github.css'

// 配置 marked 选项
marked.setOptions({
  breaks: true,      // 允许换行符转换为 <br>
  gfm: true,         // 启用 GitHub Flavored Markdown
  headerIds: false,  // 禁用自动添加 header id，避免冲突
  mangle: false      // 禁用 email 地址混淆
})

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

// HTML 转义函数（防止 XSS）
const escapeHtml = (text) => {
  const div = document.createElement('div')
  div.textContent = text
  return div.innerHTML
}

// 创建自定义 renderer
const createRenderer = (contextDocs) => {
  const renderer = new marked.Renderer()
  
  // 自定义链接渲染
  renderer.link = function({ href, title, text }) {
    // 快速判断：text 必须是 "引用N" 格式
    const citeMatch = text.match(/^引用(\d+)$/)
    if (!citeMatch) {
      // 普通链接
      return `<a href="${href}" title="${title || ''}" target="_blank" rel="noopener noreferrer">${text}</a>`
    }
    
    // 是引用链接
    const citeNum = citeMatch[1]
    const docIndex = parseInt(citeNum) - 1
    const doc = contextDocs[docIndex]
    
    console.log('[ChatMessage] Rendering cite link:', { citeNum, docIndex, doc: !!doc, href })
    
    // 获取文档信息
    const docTitle = doc ? (doc.title || doc.metadata?.title || `文档 ${citeNum}`) : `文档 ${citeNum}`
    const fileName = doc ? (doc.file_name || doc.metadata?.file_name || doc.title || '') : ''
    const docId = doc ? (doc.doc_id || doc.metadata?.doc_id || '') : ''
    
    return `<a href="${href}" class="cite-link" data-doc-title="${docTitle}" data-file-name="${fileName}" data-doc-id="${docId}" data-download-url="${href}" title="点击下载：${docTitle}" target="_blank">[引用${citeNum}]</a>`
  }
  
  // 自定义代码块渲染
  renderer.code = function({ text, lang }) {
    if (lang && hljs.getLanguage(lang)) {
      const highlighted = hljs.highlight(text, { language: lang }).value
      return `<pre><code class="hljs language-${lang}">${highlighted}</code></pre>`
    }
    const highlighted = hljs.highlightAuto(text).value
    return `<pre><code class="hljs">${highlighted}</code></pre>`
  }
  
  return renderer
}

// 使用 ref 存储渲染内容，配合 watch 实现更细粒度的控制
const renderedContent = ref('')

// 清理和修复可能损坏的 Markdown 内容
const sanitizeMarkdown = (content) => {
  if (!content) return ''
  
  let cleaned = content
  
  // 修复常见的不完整 Markdown 语法（流式输出时可能出现）
  // 1. 修复未闭合的代码块
  const codeBlockMatches = cleaned.match(/```/g)
  if (codeBlockMatches && codeBlockMatches.length % 2 !== 0) {
    cleaned += '\n```'
  }
  
  // 2. 修复未闭合的行内代码
  const inlineCodeMatches = cleaned.match(/`/g)
  if (inlineCodeMatches && inlineCodeMatches.length % 2 !== 0) {
    cleaned += '`'
  }
  
  // 3. 修复不完整的 HTML 标签（仅处理真正的未闭合标签）
  // 检查行尾是否有未闭合的 <tag 形式（没有 >）
  cleaned = cleaned.replace(/<([a-zA-Z][a-zA-Z0-9]*)\s*$/g, '&lt;$1')
  
  // 4. 确保列表项格式正确
  // 将连续的换行后的列表符号统一格式
  cleaned = cleaned.replace(/\n\s*[-*]\s/g, '\n- ')
  cleaned = cleaned.replace(/\n\s*(\d+)\.\s/g, '\n$1. ')
  
  return cleaned
}

// 预处理内容：将纯文本 [引用N] 转换为 Markdown 链接 [引用N](URL)
const preprocessContent = (content, contextDocs) => {
  if (!content || !contextDocs || contextDocs.length === 0) {
    return content
  }
  
  // 只处理纯文本 [引用N]，不处理已经是链接的 [引用N](...)
  // 使用简单的字符串替换，避免复杂正则
  let result = content
  contextDocs.forEach((doc, index) => {
    const num = index + 1
    const plainCite = `[引用${num}]`
    // 检查是否是纯文本（后面没有紧跟左括号）
    const regex = new RegExp(`\\[引用${num}\\](?!\\()`, 'g')
    if (regex.test(result)) {
      const downloadUrl = doc.download_url || `/files/download/${doc.doc_id}`
      result = result.replace(regex, `[引用${num}](${downloadUrl})`)
    }
  })
  return result
}

// 实时监听 content 和 contextDocs 变化并更新渲染
watch(
  [() => props.content, () => props.contextDocs],
  async ([newContent, newContextDocs]) => {
    console.log('[ChatMessage] Content or contextDocs changed:', { 
      contentLength: newContent?.length, 
      docsCount: newContextDocs?.length 
    })
    
    if (!newContent) {
      renderedContent.value = ''
      return
    }
    
    // 预处理内容（传入最新的 contextDocs）
    let processedContent = preprocessContent(newContent, newContextDocs)
    
    // 清理和修复 Markdown 内容
    processedContent = sanitizeMarkdown(processedContent)
    
    try {
      // 创建 renderer（传入最新的 contextDocs）并解析（marked v12 是异步的）
      const renderer = createRenderer(newContextDocs)
      const html = await marked.parse(processedContent, { 
        renderer,
        breaks: true,
        gfm: true
      })
      renderedContent.value = html
    } catch (err) {
      console.error('[ChatMessage] Marked parse error:', err)
      // 出错时尝试用简化方式渲染
      try {
        const html = await marked.parse(processedContent, { 
          breaks: true, 
          gfm: true 
        })
        renderedContent.value = html
      } catch (e) {
        // 最后手段：显示原始内容（转义HTML防止XSS）
        renderedContent.value = `<div style="white-space: pre-wrap; word-break: break-word; font-family: inherit;">${escapeHtml(newContent)}</div>`
      }
    }
    
    // 渲染完成后绑定点击事件
    nextTick(() => {
      bindCiteLinkEvents()
    })
  },
  { immediate: true, flush: 'post' }
)

// 引用链接点击处理 - 使用事件委托
const handleCiteClick = (e) => {
  // 查找最近的 .cite-link 元素
  const link = e.target.closest('.cite-link')
  if (!link) return
  
  // 不再阻止默认行为，让链接直接跳转下载
  console.log('[ChatMessage] Cite link clicked, will download:', link.getAttribute('href'))
}

// 绑定引用链接点击事件 - 使用事件委托
const bindCiteLinkEvents = () => {
  if (!contentRef.value) return
  
  // 使用事件委托，直接绑定到容器元素
  contentRef.value.removeEventListener('click', handleCiteClick)
  contentRef.value.addEventListener('click', handleCiteClick)
  
  const citeLinks = contentRef.value.querySelectorAll('.cite-link')
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

:deep(.markdown-body h1) {
  margin: 24px 0 16px 0;
  font-weight: 600;
  font-size: 1.5em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 8px;
}

:deep(.markdown-body h2) {
  margin: 20px 0 14px 0;
  font-weight: 600;
  font-size: 1.3em;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  padding-bottom: 6px;
}

:deep(.markdown-body h3) {
  margin: 16px 0 12px 0;
  font-weight: 600;
  font-size: 1.15em;
}

:deep(.markdown-body h4,
.markdown-body h5,
.markdown-body h6) {
  margin: 14px 0 10px 0;
  font-weight: 600;
  font-size: 1em;
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

/* 任务列表样式 */
:deep(.markdown-body input[type="checkbox"]) {
  margin-right: 8px;
  vertical-align: middle;
}

:deep(.markdown-body input[type="checkbox"]:disabled) {
  cursor: default;
}

/* 删除线 */
:deep(.markdown-body del,
.markdown-body s) {
  text-decoration: line-through;
  color: rgba(255, 255, 255, 0.5);
}

/* 水平线 */
:deep(.markdown-body hr) {
  border: none;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin: 24px 0;
}

/* 上标和下标 */
:deep(.markdown-body sup) {
  font-size: 0.75em;
  vertical-align: super;
}

:deep(.markdown-body sub) {
  font-size: 0.75em;
  vertical-align: sub;
}

/* 图片样式 */
:deep(.markdown-body img) {
  max-width: 100%;
  height: auto;
  border-radius: 8px;
  margin: 8px 0;
}

/* 链接样式 */
:deep(.markdown-body a) {
  color: #667eea;
  text-decoration: none;
}

:deep(.markdown-body a:hover) {
  text-decoration: underline;
}

/* 嵌套列表 */
:deep(.markdown-body ul ul,
.markdown-body ul ol,
.markdown-body ol ul,
.markdown-body ol ol) {
  margin: 4px 0;
}

/* 定义列表 */
:deep(.markdown-body dl) {
  margin: 8px 0;
}

:deep(.markdown-body dt) {
  font-weight: 600;
  margin-top: 8px;
}

:deep(.markdown-body dd) {
  margin-left: 24px;
  color: rgba(255, 255, 255, 0.7);
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
