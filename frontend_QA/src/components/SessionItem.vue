<template>
  <div 
    :class="['session-item', { active: session.session_id === currentSessionId }]"
    @click="$emit('switch', session.session_id)"
  >
    <!-- 置顶标记 -->
    <span v-if="session.is_pinned" class="pin-badge">
      <svg viewBox="0 0 24 24" fill="currentColor" width="10" height="10">
        <path d="M16 12V4H17V2H7V4H8V12L6 14V16H11.2V22H12.8V16H18V14L16 12Z"/>
      </svg>
    </span>
    
    <!-- 编辑状态 -->
    <template v-if="editingSessionId === session.session_id">
      <input
        ref="inputRef"
        v-model="localEditingName"
        class="session-name-input"
        type="text"
        maxlength="50"
        @blur="handleBlur"
        @keydown.enter="handleSave"
        @keydown.esc="$emit('cancel-edit')"
        @click.stop
      />
      <div class="edit-actions">
        <button class="action-btn save" @click.stop="handleSave" title="保存">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </button>
        <button class="action-btn cancel" @click.stop="$emit('cancel-edit')" title="取消">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </template>
    
    <!-- 显示状态 -->
    <template v-else>
      <span class="session-name" :title="getSessionTitle(session)">
        {{ getSessionTitle(session) }}
      </span>
      <div class="session-actions">
        <button class="action-btn pin" @click.stop="$emit('toggle-pin', session)" title="置顶/取消置顶">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" :class="{ 'is-pinned': session.is_pinned }">
            <path d="M12 2L12 8M12 12L12 22M12 12L16 16M12 12L8 16" stroke-linecap="round" v-if="session.is_pinned"/>
            <path d="M16 12V4H17V2H7V4H8V12L6 14V16H11.2V22H12.8V16H18V14L16 12Z" v-else/>
          </svg>
        </button>
        <button class="action-btn edit" @click.stop="$emit('edit', session)" title="重命名">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path>
            <path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path>
          </svg>
        </button>
        <button class="action-btn delete" @click.stop="$emit('delete', session.session_id)" title="删除">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"></path>
          </svg>
        </button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  session: {
    type: Object,
    required: true
  },
  currentSessionId: {
    type: String,
    default: ''
  },
  editingSessionId: {
    type: String,
    default: ''
  },
  editingSessionName: {
    type: String,
    default: ''
  }
})

const emit = defineEmits(['switch', 'delete', 'edit', 'save-name', 'cancel-edit', 'toggle-pin', 'update:editing-name'])

const inputRef = ref(null)
const localEditingName = ref('')

// 获取会话标题
const getSessionTitle = (session) => {
  if (session.session_name) {
    return session.session_name
  }
  const date = new Date(session.last_message_at || session.created_at)
  const hours = date.getHours().toString().padStart(2, '0')
  const minutes = date.getMinutes().toString().padStart(2, '0')
  return `${hours}:${minutes} 的对话`
}

// 监听编辑状态变化
watch(() => props.editingSessionId, (newVal) => {
  if (newVal === props.session.session_id) {
    localEditingName.value = props.editingSessionName
    nextTick(() => {
      inputRef.value?.focus()
      inputRef.value?.select()
    })
  }
})

// 监听本地编辑名称变化
watch(localEditingName, (newVal) => {
  emit('update:editing-name', newVal)
})

const handleSave = () => {
  emit('save-name', props.session.session_id)
}

const handleBlur = () => {
  // 延迟执行，让点击保存按钮的事件先处理
  setTimeout(() => {
    emit('cancel-edit')
  }, 200)
}
</script>

<style scoped>
.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 2px;
  position: relative;
}

.session-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.session-item.active {
  background: rgba(102, 126, 234, 0.2);
}

.pin-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 6px;
  color: #667eea;
  flex-shrink: 0;
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

.session-name-input {
  flex: 1;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.5);
  border-radius: 4px;
  padding: 4px 8px;
  font-size: 13px;
  color: #fff;
  outline: none;
  margin-right: 4px;
}

.session-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  opacity: 0;
  transition: opacity 0.2s;
}

.session-item:hover .session-actions {
  opacity: 1;
}

.edit-actions {
  display: flex;
  align-items: center;
  gap: 2px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  background: transparent;
  border: none;
  color: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all 0.2s;
  padding: 0;
  border-radius: 4px;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.action-btn svg {
  width: 14px;
  height: 14px;
}

.action-btn.save:hover {
  color: #4caf50;
}

.action-btn.cancel:hover {
  color: #f44336;
}

.action-btn.pin:hover {
  color: #667eea;
}

.action-btn.edit:hover {
  color: #ffa726;
}

.action-btn.delete:hover {
  color: #f44336;
}

.action-btn.pin svg.is-pinned {
  color: #667eea;
  fill: rgba(102, 126, 234, 0.2);
}
</style>
