<template>
  <div class="chat-view">
    <!-- 消息列表 -->
    <div class="messages-container" ref="messagesContainer">
      <div v-if="messages.length === 0" class="welcome">
        <h2>👋 欢迎使用 Smart RAGFlow</h2>
        <p>基于 RAG 技术的智能问答系统</p>
        <div class="examples">
          <div class="example-title">示例问题：</div>
          <button 
            v-for="example in examples" 
            :key="example"
            class="example-btn"
            @click="sendExample(example)"
          >
            {{ example }}
          </button>
        </div>
      </div>
      
      <ChatMessage
        v-for="(msg, index) in messages"
        :key="index"
        :role="msg.role"
        :content="msg.content"
        :is-streaming="msg.isStreaming"
        :context-docs="msg.contextDocs || []"
      />
      
      <!-- 错误提示（独立显示，不污染聊天内容） -->
      <div v-if="error" class="error-toast">
        <div class="error-icon">⚠️</div>
        <div class="error-content">
          <div class="error-title">出错了</div>
          <div class="error-desc">{{ error }}</div>
        </div>
        <button class="error-close" @click="error = ''">✕</button>
      </div>
    </div>

    <!-- 输入区域 -->
    <div class="input-container">
      <div class="input-wrapper">
        <textarea
          v-model="inputMessage"
          class="message-input"
          placeholder="输入您的问题..."
          rows="1"
          @keydown.enter.prevent="handleEnter"
          @input="autoResize"
          ref="inputRef"
        ></textarea>
        <button 
          class="send-btn"
          :disabled="!inputMessage.trim() || isLoading"
          @click="sendMessage"
        >
          <svg v-if="!isLoading" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"></line>
            <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
          </svg>
          <svg v-else class="spin" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 6v6l4 2"></path>
          </svg>
        </button>
      </div>
      <div class="hint">Enter 发送，Shift + Enter 换行</div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import ChatMessage from '../components/ChatMessage.vue'
import { streamChatCompletion } from '../utils/api.js'

const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const error = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)

const examples = [
  '什么是 RAG 技术？',
  '解释一下 Java 的内存模型',
  '如何优化 Elasticsearch 查询性能？'
]

// 自动调整输入框高度
const autoResize = () => {
  const textarea = inputRef.value
  if (textarea) {
    textarea.style.height = 'auto'
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px'
  }
}

// 处理回车键
const handleEnter = (e) => {
  if (e.shiftKey) {
    return
  }
  sendMessage()
}

// 滚动到底部（带节流）
let scrollTimeout = null
const scrollToBottom = () => {
  if (scrollTimeout) return
  scrollTimeout = setTimeout(() => {
    scrollTimeout = null
    nextTick(() => {
      if (messagesContainer.value) {
        messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
      }
    })
  }, 16) // 约60fps，避免过于频繁的DOM操作
}

// 发送示例
const sendExample = (example) => {
  inputMessage.value = example
  sendMessage()
}

// 发送消息
const sendMessage = async () => {
  const message = inputMessage.value.trim()
  if (!message || isLoading.value) return

  // 添加用户消息
  messages.value.push({
    role: 'user',
    content: message
  })

  // 清空输入
  inputMessage.value = ''
  if (inputRef.value) {
    inputRef.value.style.height = 'auto'
  }

  // 添加助手消息占位
  messages.value.push({
    role: 'assistant',
    content: '',
    isStreaming: true,
    contextDocs: []
  })
  
  // 记录助手消息的索引
  const assistantIndex = messages.value.length - 1
  
  // 存储检索到的文档元数据
  let contextDocs = []
  
  isLoading.value = true
  error.value = ''
  scrollToBottom()

  // 调用流式接口
  await streamChatCompletion(
    message,
    // onChunk - 接收流式数据
    (content) => {
      messages.value[assistantIndex].content += content
      scrollToBottom()
    },
    // onDone - 完成
    () => {
      messages.value[assistantIndex].isStreaming = false
      messages.value[assistantIndex].contextDocs = contextDocs
      isLoading.value = false
      scrollToBottom()
    },
    // onError - 错误（不污染聊天内容，只显示错误提示）
    (errMsg) => {
      messages.value[assistantIndex].isStreaming = false
      messages.value[assistantIndex].contextDocs = contextDocs
      // 如果助手消息为空，移除这个空消息
      if (!messages.value[assistantIndex].content.trim()) {
        messages.value.splice(assistantIndex, 1)
      }
      isLoading.value = false
      error.value = errMsg
      scrollToBottom()
    },
    // onDocs - 接收文档元数据
    (docs) => {
      contextDocs = docs
      messages.value[assistantIndex].contextDocs = docs
    }
  )
}
</script>

<style scoped>
.chat-view {
  width: 100%;
  max-width: 900px;
  height: calc(100vh - 140px);
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.08);
  overflow: hidden;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  scroll-behavior: smooth;
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.messages-container::-webkit-scrollbar-thumb {
  background: #ccc;
  border-radius: 3px;
}

.welcome {
  text-align: center;
  padding: 60px 20px;
  color: #666;
}

.welcome h2 {
  font-size: 24px;
  margin-bottom: 12px;
  color: #333;
}

.welcome p {
  font-size: 16px;
  margin-bottom: 30px;
}

.examples {
  max-width: 500px;
  margin: 0 auto;
}

.example-title {
  font-size: 14px;
  color: #999;
  margin-bottom: 12px;
}

.example-btn {
  display: block;
  width: 100%;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: #f5f5f5;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
  color: #555;
  text-align: left;
}

.example-btn:hover {
  background: #e8f0fe;
  border-color: #667eea;
  color: #667eea;
}

.input-container {
  padding: 16px 20px 20px;
  border-top: 1px solid #eee;
  background: white;
}

.input-wrapper {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  background: #f8f9fa;
  border-radius: 12px;
  padding: 8px;
  border: 1px solid #e0e0e0;
  transition: border-color 0.2s;
}

.input-wrapper:focus-within {
  border-color: #667eea;
  background: white;
}

.message-input {
  flex: 1;
  border: none;
  background: transparent;
  resize: none;
  font-size: 15px;
  line-height: 1.5;
  padding: 8px;
  outline: none;
  font-family: inherit;
  max-height: 150px;
  min-height: 24px;
}

.send-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #667eea;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #5a6fd6;
  transform: scale(1.05);
}

.send-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.hint {
  text-align: center;
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

/* 错误提示（独立显示，不污染聊天内容） */
.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  background: #fff3f3;
  border: 1px solid #ffcdd2;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(198, 40, 40, 0.15);
  z-index: 100;
  max-width: 500px;
  animation: slideDown 0.3s ease;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateX(-50%) translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }
}

.error-icon {
  font-size: 20px;
  flex-shrink: 0;
}

.error-content {
  flex: 1;
  min-width: 0;
}

.error-title {
  font-size: 14px;
  font-weight: 600;
  color: #c62828;
  margin-bottom: 4px;
}

.error-desc {
  font-size: 13px;
  color: #d32f2f;
  line-height: 1.5;
}

.error-close {
  background: none;
  border: none;
  color: #999;
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  line-height: 1;
  transition: color 0.2s;
}

.error-close:hover {
  color: #666;
}
</style>
