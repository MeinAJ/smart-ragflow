<template>
  <div class="chat-layout">
    <!-- 左侧会话列表侧边栏 -->
    <aside class="sidebar">
      <div class="sidebar-header">
        <div class="logo">
          <span class="logo-icon">🤖</span>
          <span class="logo-text">Smart RAGFlow</span>
        </div>
        <button class="new-chat-btn" @click="createNewSession">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          <span>开启新对话</span>
        </button>
      </div>
      
      <div class="session-list">
        <!-- 今天 -->
        <!-- 置顶会话 -->
        <div v-if="sessionList.filter(s => s.is_pinned).length > 0" class="session-group">
          <div class="group-title">
            <svg class="pin-icon" viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
              <path d="M16 12V4H17V2H7V4H8V12L6 14V16H11.2V22H12.8V16H18V14L16 12Z"/>
            </svg>
            置顶
          </div>
          <SessionItem 
            v-for="session in sessionList.filter(s => s.is_pinned)" 
            :key="session.session_id"
            :session="session"
            :current-session-id="currentSessionId"
            :editing-session-id="editingSessionId"
            :editing-session-name="editingSessionName"
            @switch="switchSession(session)"
            @delete="confirmDeleteSession"
            @edit="startEditSessionName"
            @save-name="saveSessionName"
            @cancel-edit="cancelEditSessionName"
            @toggle-pin="togglePinSession"
            @update:editing-name="editingSessionName = $event"
          />
        </div>
        
        <!-- 今天 -->
        <div v-if="todaySessions.filter(s => !s.is_pinned).length > 0" class="session-group">
          <div class="group-title">今天</div>
          <SessionItem 
            v-for="session in todaySessions.filter(s => !s.is_pinned)" 
            :key="session.session_id"
            :session="session"
            :current-session-id="currentSessionId"
            :editing-session-id="editingSessionId"
            :editing-session-name="editingSessionName"
            @switch="switchSession(session)"
            @delete="confirmDeleteSession"
            @edit="startEditSessionName"
            @save-name="saveSessionName"
            @cancel-edit="cancelEditSessionName"
            @toggle-pin="togglePinSession"
            @update:editing-name="editingSessionName = $event"
          />
        </div>
        
        <!-- 昨天 -->
        <div v-if="yesterdaySessions.filter(s => !s.is_pinned).length > 0" class="session-group">
          <div class="group-title">昨天</div>
          <SessionItem 
            v-for="session in yesterdaySessions.filter(s => !s.is_pinned)" 
            :key="session.session_id"
            :session="session"
            :current-session-id="currentSessionId"
            :editing-session-id="editingSessionId"
            :editing-session-name="editingSessionName"
            @switch="switchSession(session)"
            @delete="confirmDeleteSession"
            @edit="startEditSessionName"
            @save-name="saveSessionName"
            @cancel-edit="cancelEditSessionName"
            @toggle-pin="togglePinSession"
            @update:editing-name="editingSessionName = $event"
          />
        </div>
        
        <!-- 7天内 -->
        <div v-if="last7DaysSessions.filter(s => !s.is_pinned).length > 0" class="session-group">
          <div class="group-title">7天内</div>
          <SessionItem 
            v-for="session in last7DaysSessions.filter(s => !s.is_pinned)" 
            :key="session.session_id"
            :session="session"
            :current-session-id="currentSessionId"
            :editing-session-id="editingSessionId"
            :editing-session-name="editingSessionName"
            @switch="switchSession(session)"
            @delete="confirmDeleteSession"
            @edit="startEditSessionName"
            @save-name="saveSessionName"
            @cancel-edit="cancelEditSessionName"
            @toggle-pin="togglePinSession"
            @update:editing-name="editingSessionName = $event"
          />
        </div>
        
        <!-- 更早 -->
        <div v-if="olderSessions.filter(s => !s.is_pinned).length > 0" class="session-group">
          <div class="group-title">更早</div>
          <SessionItem 
            v-for="session in olderSessions.filter(s => !s.is_pinned)" 
            :key="session.session_id"
            :session="session"
            :current-session-id="currentSessionId"
            :editing-session-id="editingSessionId"
            :editing-session-name="editingSessionName"
            @switch="switchSession(session)"
            @delete="confirmDeleteSession"
            @edit="startEditSessionName"
            @save-name="saveSessionName"
            @cancel-edit="cancelEditSessionName"
            @toggle-pin="togglePinSession"
            @update:editing-name="editingSessionName = $event"
          />
        </div>
        
        <div v-if="sessionList.length === 0" class="empty-sessions">
          暂无历史对话
        </div>
      </div>
      
      <!-- 用户信息 -->
      <div class="user-info">
        <div class="user-avatar">
          {{ userAvatar }}
        </div>
        <span class="user-name">{{ user?.nickname || user?.username || '用户' }}</span>
        <button class="logout-btn" @click="handleLogout" title="退出登录">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"></path>
          </svg>
        </button>
      </div>
    </aside>

    <!-- 主聊天区域 -->
    <main class="chat-main">
      <!-- 会话标题栏 -->
      <div v-if="currentSessionId && currentSessionName" class="session-header">
        <span class="session-header-title">{{ currentSessionName }}</span>
      </div>
      
      <!-- 消息列表 -->
      <div class="messages-container" ref="messagesContainer">
        <!-- 欢迎页面 -->
        <div v-if="messages.length === 0" class="welcome">
          <div class="welcome-icon">🐋</div>
          <h2>今天有什么可以帮到你？</h2>
          
          <div class="input-area">
            <div class="input-wrapper">
              <textarea
                v-model="inputMessage"
                class="message-input"
                placeholder="给 Smart RAGFlow 发送消息..."
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
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="22" y1="2" x2="11" y2="13"></line>
                  <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
              </button>
            </div>
            <div class="input-options">
              <button class="option-btn">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="12" cy="12" r="3"></circle>
                  <path d="M12 1v6m0 6v6m4.22-10.22l4.24-4.24M6.34 17.66l-4.24 4.24M23 12h-6m-6 0H1m20.24 4.24l-4.24-4.24M6.34 6.34L2.1 2.1"></path>
                </svg>
                深度思考
              </button>
              <button class="option-btn active">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                </svg>
                智能搜索
              </button>
            </div>
          </div>
        </div>
        
        <!-- 加载历史消息提示 -->
        <div v-if="isLoadingHistory" class="loading-history">
          <div class="spinner"></div>
          <span>加载历史消息...</span>
        </div>
        
        <!-- 聊天消息列表 -->
        <template v-else-if="messages.length > 0">
          <ChatMessage
            v-for="(msg, index) in messages"
            :key="index"
            :role="msg.role"
            :content="msg.content"
            :is-streaming="msg.isStreaming"
            :context-docs="msg.contextDocs || []"
          />
        </template>
        
        <!-- 错误提示 -->
        <div v-if="error" class="error-toast">
          <div class="error-icon">⚠️</div>
          <div class="error-content">{{ error }}</div>
          <button class="error-close" @click="error = ''">✕</button>
        </div>
      </div>

      <!-- 底部输入区域（有消息时显示） -->
      <div v-if="messages.length > 0" class="chat-input-container">
        <div class="input-wrapper">
          <textarea
            v-model="inputMessage"
            class="message-input"
            placeholder="输入消息..."
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
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import ChatMessage from '../components/ChatMessage.vue'
import SessionItem from '../components/SessionItem.vue'
import { streamChatCompletion, getSessionList, getSessionMessages, deleteSession, updateSessionName, pinSession } from '../utils/api.js'
import { getUser, logout } from '../utils/auth.js'

const router = useRouter()

// 状态管理
const messages = ref([])
const inputMessage = ref('')
const isLoading = ref(false)
const isLoadingHistory = ref(false)  // 新增：加载历史消息状态
const error = ref('')
const messagesContainer = ref(null)
const inputRef = ref(null)
const currentSessionId = ref('')
const currentSessionName = ref('')   // 新增：当前会话名称
const sessionList = ref([])
const user = ref(getUser())

// 用户头像
const userAvatar = computed(() => {
  const name = user.value?.nickname || user.value?.username || '用户'
  return name.charAt(0).toUpperCase()
})

// 按时间分组的会话列表
const todaySessions = computed(() => filterSessionsByDate(0))
const yesterdaySessions = computed(() => filterSessionsByDate(1))
const last7DaysSessions = computed(() => filterSessionsByDateRange(2, 7))
const olderSessions = computed(() => filterSessionsByDateRange(8, Infinity))

function filterSessionsByDate(daysAgo) {
  const now = new Date()
  const targetDate = new Date(now.getTime() - daysAgo * 24 * 60 * 60 * 1000)
  
  return sessionList.value.filter(session => {
    const sessionDate = new Date(session.last_message_at || session.created_at)
    return isSameDay(sessionDate, targetDate)
  })
}

function filterSessionsByDateRange(startDays, endDays) {
  const now = new Date()
  const startDate = new Date(now.getTime() - endDays * 24 * 60 * 60 * 1000)
  const endDate = new Date(now.getTime() - startDays * 24 * 60 * 60 * 1000)
  
  return sessionList.value.filter(session => {
    const sessionDate = new Date(session.last_message_at || session.created_at)
    return sessionDate >= startDate && sessionDate <= endDate
  })
}

// 编辑会话名称状态
const editingSessionId = ref('')
const editingSessionName = ref('')

function isSameDay(date1, date2) {
  return date1.getFullYear() === date2.getFullYear() &&
         date1.getMonth() === date2.getMonth() &&
         date1.getDate() === date2.getDate()
}

// 生成新的会话ID
const generateSessionId = () => {
  return `sess_${Date.now()}_${Math.random().toString(36).substring(2, 10)}`
}

// 获取会话标题
const getSessionTitle = (session) => {
  // 优先使用 session_name 字段
  if (session.session_name) {
    return session.session_name
  }
  // 如果没有名称，使用最后消息时间
  const date = new Date(session.last_message_at || session.created_at)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes} 的对话`
}

// 开始编辑会话名称
const startEditSessionName = (session) => {
  editingSessionId.value = session.session_id
  editingSessionName.value = session.session_name || getSessionTitle(session)
}

// 保存会话名称
const saveSessionName = async (sessionId) => {
  const newName = editingSessionName.value.trim()
  if (!newName) {
    editingSessionId.value = ''
    return
  }
  
  const success = await updateSessionName(sessionId, newName)
  if (success) {
    // 更新本地数据
    const session = sessionList.value.find(s => s.session_id === sessionId)
    if (session) {
      session.session_name = newName
    }
    editingSessionId.value = ''
  } else {
    error.value = '更新会话名称失败'
  }
}

// 取消编辑
const cancelEditSessionName = () => {
  editingSessionId.value = ''
  editingSessionName.value = ''
}

// 切换置顶状态
const togglePinSession = async (session) => {
  const newPinStatus = !session.is_pinned
  const success = await pinSession(session.session_id, newPinStatus)
  if (success) {
    session.is_pinned = newPinStatus
    // 重新排序会话列表
    sessionList.value.sort((a, b) => {
      if (a.is_pinned !== b.is_pinned) {
        return b.is_pinned - a.is_pinned
      }
      return new Date(b.last_message_at || b.created_at) - new Date(a.last_message_at || a.created_at)
    })
  } else {
    error.value = '置顶会话失败'
  }
}

// 创建新会话
const createNewSession = () => {
  currentSessionId.value = ''
  currentSessionName.value = ''
  messages.value = []
  error.value = ''
  console.log('[ChatView] Created new session')
}

// 切换会话
const switchSession = async (session) => {
  const sessionId = session.session_id
  if (sessionId === currentSessionId.value) return
  
  currentSessionId.value = sessionId
  currentSessionName.value = session.session_name || getSessionTitle(session)
  messages.value = []
  error.value = ''
  isLoadingHistory.value = true
  
  try {
    // 加载该会话的历史消息
    await loadSessionMessages(sessionId)
    console.log('[ChatView] Switched to session:', sessionId)
  } finally {
    isLoadingHistory.value = false
  }
}

// 加载会话消息
const loadSessionMessages = async (sessionId) => {
  const historyMessages = await getSessionMessages(sessionId, 100)
  if (historyMessages && historyMessages.length > 0) {
    // 按时间顺序排序（旧的在前面）
    const sortedMessages = historyMessages.sort((a, b) => 
      new Date(a.created_at) - new Date(b.created_at)
    )
    
    // 转换为组件需要的格式
    messages.value = sortedMessages.map(msg => ({
      role: msg.role,
      content: msg.content,
      isStreaming: false,
      contextDocs: msg.context_docs || []
    }))
    
    // 滚动到底部
    nextTick(() => {
      scrollToBottom()
    })
  } else {
    messages.value = []
  }
}

// 确认删除会话
const confirmDeleteSession = async (sessionId) => {
  if (!confirm('确定要删除这个会话吗？')) return
  
  const success = await deleteSession(sessionId)
  if (success) {
    // 如果删除的是当前会话，清空当前会话状态
    if (sessionId === currentSessionId.value) {
      currentSessionId.value = ''
      currentSessionName.value = ''
      messages.value = []
    }
    // 刷新列表
    await loadSessionList()
  } else {
    error.value = '删除会话失败'
  }
}

// 加载会话列表
const loadSessionList = async () => {
  const sessions = await getSessionList(50)
  sessionList.value = sessions
}

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

// 滚动到底部
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
  }, 16)
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

  // 如果是新会话，生成新的sessionId
  let sessionId = currentSessionId.value
  if (!sessionId) {
    sessionId = generateSessionId()
    currentSessionId.value = sessionId
  }

  // 添加用户消息
  if (messages.value.length === 0) {
    messages.value = [{
      role: 'user',
      content: message
    }]
  } else {
    messages.value.push({
      role: 'user',
      content: message
    })
  }

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
  
  const assistantIndex = messages.value.length - 1
  let contextDocs = []
  
  isLoading.value = true
  error.value = ''
  scrollToBottom()

  // 调用流式接口
  await streamChatCompletion(
    message,
    (content) => {
      messages.value[assistantIndex].content += content
      scrollToBottom()
    },
    () => {
      messages.value[assistantIndex].isStreaming = false
      messages.value[assistantIndex].contextDocs = contextDocs
      isLoading.value = false
      scrollToBottom()
      loadSessionList()
    },
    (errMsg) => {
      messages.value[assistantIndex].isStreaming = false
      messages.value[assistantIndex].contextDocs = contextDocs
      if (!messages.value[assistantIndex].content.trim()) {
        messages.value.splice(assistantIndex, 1)
      }
      isLoading.value = false
      error.value = errMsg
      scrollToBottom()
    },
    (docs) => {
      contextDocs = docs
      messages.value[assistantIndex].contextDocs = docs
    },
    sessionId
  )
}

// 退出登录
const handleLogout = async () => {
  await logout()
}

// 组件挂载时
onMounted(() => {
  createNewSession()
  loadSessionList()
  setInterval(loadSessionList, 30000)
})
</script>

<style scoped>
.chat-layout {
  display: flex;
  width: 100%;
  height: 100vh;
  background: #1a1a2e;
}

/* 侧边栏 */
.sidebar {
  width: 260px;
  background: #16162a;
  border-right: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.logo {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}

.logo-icon {
  font-size: 24px;
}

.logo-text {
  font-size: 16px;
  font-weight: 600;
  color: #fff;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px;
  background: rgba(102, 126, 234, 0.2);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 8px;
  color: #667eea;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.new-chat-btn:hover {
  background: rgba(102, 126, 234, 0.3);
}

.new-chat-btn svg {
  width: 16px;
  height: 16px;
}

/* 会话列表 */
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.session-group {
  margin-bottom: 16px;
}

.group-title {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.4);
  padding: 8px 12px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 6px;
}

.group-title .pin-icon {
  color: #667eea;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 2px;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.session-item.active {
  background: rgba(102, 126, 234, 0.2);
}

.session-name {
  flex: 1;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  padding-right: 8px;
}

.delete-btn {
  opacity: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.3);
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
}

.session-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  color: #f44336;
}

.delete-btn svg {
  width: 14px;
  height: 14px;
}

.empty-sessions {
  text-align: center;
  padding: 40px 20px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 13px;
}

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.user-name {
  flex: 1;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.logout-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
  border-radius: 6px;
}

.logout-btn:hover {
  color: rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.1);
}

.logout-btn svg {
  width: 18px;
  height: 18px;
}

/* 主聊天区域 */
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #1a1a2e;
  min-width: 0;
  align-items: center;
}

/* 会话标题栏 */
.session-header {
  width: 100%;
  max-width: 850px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  align-items: center;
  justify-content: center;
}

.session-header-title {
  font-size: 15px;
  font-weight: 500;
  color: rgba(255, 255, 255, 0.9);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 100%;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  width: 100%;
  max-width: 850px;
}

/* 加载历史消息 */
.loading-history {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 40px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 14px;
}

.loading-history .spinner {
  width: 20px;
  height: 20px;
  border: 2px solid rgba(255, 255, 255, 0.1);
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.messages-container::-webkit-scrollbar {
  width: 6px;
}

.messages-container::-webkit-scrollbar-track {
  background: transparent;
}

.messages-container::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

/* 欢迎页面 */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
  padding: 40px 20px;
}

.welcome-icon {
  font-size: 48px;
  margin-bottom: 16px;
}

.welcome h2 {
  font-size: 24px;
  font-weight: 500;
  color: #fff;
  margin: 0 0 32px;
}

.input-area {
  width: 100%;
  max-width: 850px;
}

.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  background: #252542;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 12px 16px;
  transition: all 0.2s;
}

.input-wrapper:focus-within {
  border-color: rgba(102, 126, 234, 0.5);
  background: #2d2d52;
}

.message-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #fff;
  font-size: 15px;
  line-height: 1.6;
  resize: none;
  outline: none;
  min-height: 24px;
  max-height: 150px;
}

.message-input::placeholder {
  color: rgba(255, 255, 255, 0.3);
}

.send-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: #667eea;
  border: none;
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}

.send-btn:hover:not(:disabled) {
  background: #5a6fd6;
  transform: scale(1.05);
}

.send-btn:disabled {
  background: rgba(102, 126, 234, 0.3);
  cursor: not-allowed;
}

.send-btn svg {
  width: 18px;
  height: 18px;
}

.input-options {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-left: 4px;
}

.option-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  color: rgba(255, 255, 255, 0.5);
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.option-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: rgba(255, 255, 255, 0.8);
}

.option-btn.active {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.5);
  color: #667eea;
}

.option-btn svg {
  width: 14px;
  height: 14px;
}

/* 底部输入区域 */
.chat-input-container {
  padding: 16px 20px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  width: 100%;
  max-width: 850px;
}

.chat-input-container .input-wrapper {
  max-width: 850px;
  margin: 0 auto;
}

/* 错误提示 */
.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  background: rgba(244, 67, 54, 0.1);
  border: 1px solid rgba(244, 67, 54, 0.3);
  border-radius: 10px;
  color: #f44336;
  font-size: 14px;
  z-index: 100;
}

.error-icon {
  font-size: 18px;
}

.error-close {
  background: none;
  border: none;
  color: inherit;
  cursor: pointer;
  font-size: 16px;
  padding: 0;
  margin-left: 8px;
}

/* 响应式 */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: 0;
    top: 0;
    bottom: 0;
    z-index: 100;
    transform: translateX(-100%);
    transition: transform 0.3s;
  }
  
  .sidebar.open {
    transform: translateX(0);
  }
}
</style>
