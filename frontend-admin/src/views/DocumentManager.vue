<template>
  <div class="document-manager">
    <!-- 操作栏 -->
    <div class="operation-bar">
      <div class="left-operations">
        <el-button type="primary" @click="showUploadDialog">
          <el-icon><Plus /></el-icon>
          上传文档
        </el-button>
        <el-button @click="refreshList">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div class="right-operations">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索文档..."
          clearable
          style="width: 250px"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
    </div>

    <!-- 文档列表 -->
    <el-card class="document-table-card">
      <el-table
        :data="documents"
        v-loading="loading"
        stripe
        style="width: 100%"
      >
        <el-table-column type="index" width="50" />
        
        <el-table-column label="文档名称" min-width="200">
          <template #default="{ row }">
            <div class="doc-name">
              <el-icon :size="20" class="doc-icon">
                <Document v-if="isTextFile(row.file_type)" />
                <Folder v-else-if="row.file_type === 'folder'" />
                <Files v-else />
              </el-icon>
              <div class="doc-info">
                <span class="name">{{ row.title || row.file_name }}</span>
                <span class="type">{{ row.file_type?.toUpperCase() }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="文档ID" width="220">
          <template #default="{ row }">
            <el-tooltip :content="row.doc_id" placement="top">
              <span class="doc-id">{{ truncateId(row.doc_id) }}</span>
            </el-tooltip>
            <el-button
              link
              type="primary"
              size="small"
              @click="copyId(row.doc_id)"
            >
              <el-icon><CopyDocument /></el-icon>
            </el-button>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="文件大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>

        <el-table-column label="更新时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.updated_at) }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="280" fixed="right">
          <template #default="{ row }">
            <el-button
              type="primary"
              size="small"
              :loading="row.parsing"
              @click="handleParse(row)"
            >
              <el-icon><VideoPlay v-if="!row.parsing" /></el-icon>
              {{ row.parsing ? '解析中' : '解析' }}
            </el-button>
            
            <el-button
              type="info"
              size="small"
              @click="handleEdit(row)"
            >
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            
            <el-popconfirm
              title="确定删除该文档吗？"
              confirm-button-text="确定"
              cancel-button-text="取消"
              @confirm="handleDelete(row)"
            >
              <template #reference>
                <el-button
                  type="danger"
                  size="small"
                >
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="pagination.page"
          v-model:page-size="pagination.size"
          :page-sizes="[10, 20, 50, 100]"
          :total="pagination.total"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 上传对话框 -->
    <el-dialog
      v-model="uploadDialog.visible"
      title="上传文档"
      width="500px"
    >
      <el-form :model="uploadForm" label-width="80px">
        <el-form-item label="选择文件">
          <el-upload
            ref="uploadRef"
            action=""
            :auto-upload="false"
            :on-change="handleFileChange"
            :on-remove="handleFileRemove"
            :limit="1"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              拖拽文件到此处或 <em>点击上传</em>
            </div>
            <template #tip>
              <div class="el-upload__tip">
                支持 PDF、DOCX、TXT、MD、XLSX、PPTX 等格式，单个文件不超过 50MB
              </div>
            </template>
          </el-upload>
        </el-form-item>
        
        <el-form-item label="文档标题">
          <el-input 
            v-model="uploadForm.title" 
            placeholder="可选，默认为文件名"
          />
        </el-form-item>
        
        <el-form-item label="文档描述">
          <el-input 
            v-model="uploadForm.description" 
            type="textarea" 
            :rows="3"
            placeholder="可选"
          />
        </el-form-item>
        
        <el-form-item label="立即解析">
          <el-switch v-model="uploadForm.parseImmediately" />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="uploadDialog.visible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitUpload"
          :loading="uploadDialog.loading"
        >
          上传
        </el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialog.visible"
      title="编辑文档"
      width="500px"
    >
      <el-form :model="editForm" label-width="80px">
        <el-form-item label="文档标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="文档描述">
          <el-input 
            v-model="editForm.description" 
            type="textarea" 
            :rows="3"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button 
          type="primary" 
          @click="submitEdit"
          :loading="editDialog.loading"
        >
          保存
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDocuments,
  uploadDocument,
  deleteDocument,
  updateDocument,
  parseDocument
} from '../api/documents.js'

// 文档列表
const documents = ref([])
const loading = ref(false)
const searchKeyword = ref('')

// 分页
const pagination = reactive({
  page: 1,
  size: 10,
  total: 0
})

// 上传对话框
const uploadDialog = reactive({
  visible: false,
  loading: false
})

// 上传表单
const uploadForm = reactive({
  title: '',
  description: '',
  parseImmediately: true
})

const uploadRef = ref(null)
const selectedFile = ref(null)

// 编辑对话框
const editDialog = reactive({
  visible: false,
  loading: false,
  docId: ''
})

const editForm = reactive({
  title: '',
  description: ''
})

// 获取文档列表
const fetchDocuments = async () => {
  loading.value = true
  try {
    const res = await getDocuments({
      page: pagination.page,
      size: pagination.size,
      keyword: searchKeyword.value
    })
    documents.value = res.items || []
    pagination.total = res.total || 0
  } catch (error) {
    ElMessage.error('获取文档列表失败：' + error)
  } finally {
    loading.value = false
  }
}

// 刷新列表
const refreshList = () => {
  pagination.page = 1
  fetchDocuments()
}

// 搜索
const handleSearch = () => {
  pagination.page = 1
  fetchDocuments()
}

// 分页变化
const handlePageChange = (page) => {
  pagination.page = page
  fetchDocuments()
}

const handleSizeChange = (size) => {
  pagination.size = size
  pagination.page = 1
  fetchDocuments()
}

// 显示上传对话框
const showUploadDialog = () => {
  uploadDialog.visible = true
  uploadForm.title = ''
  uploadForm.description = ''
  uploadForm.parseImmediately = true
  selectedFile.value = null
  if (uploadRef.value) {
    uploadRef.value.clearFiles()
  }
}

// 文件选择
const handleFileChange = (file) => {
  selectedFile.value = file.raw
  if (!uploadForm.title) {
    uploadForm.title = file.name.replace(/\.[^/.]+$/, '')
  }
}

const handleFileRemove = () => {
  selectedFile.value = null
}

// 提交上传
const submitUpload = async () => {
  if (!selectedFile.value) {
    ElMessage.warning('请选择要上传的文件')
    return
  }

  uploadDialog.loading = true
  try {
    const res = await uploadDocument(selectedFile.value, {
      title: uploadForm.title,
      description: uploadForm.description
    })
    
    ElMessage.success('上传成功')
    uploadDialog.visible = false
    
    // 如果选择了立即解析
    if (uploadForm.parseImmediately && res.doc_id) {
      await handleParse({ doc_id: res.doc_id, title: uploadForm.title })
    }
    
    fetchDocuments()
  } catch (error) {
    ElMessage.error('上传失败：' + error)
  } finally {
    uploadDialog.loading = false
  }
}

// 解析文档
const handleParse = async (row) => {
  row.parsing = true
  try {
    await parseDocument(row.doc_id)
    ElMessage.success(`「${row.title || '文档'}」解析任务已启动`)
    // 3秒后刷新状态
    setTimeout(fetchDocuments, 3000)
  } catch (error) {
    ElMessage.error('解析失败：' + error)
  } finally {
    row.parsing = false
  }
}

// 编辑文档
const handleEdit = (row) => {
  editDialog.docId = row.doc_id
  editForm.title = row.title || row.file_name
  editForm.description = row.description || ''
  editDialog.visible = true
}

// 提交编辑
const submitEdit = async () => {
  editDialog.loading = true
  try {
    await updateDocument(editDialog.docId, editForm)
    ElMessage.success('更新成功')
    editDialog.visible = false
    fetchDocuments()
  } catch (error) {
    ElMessage.error('更新失败：' + error)
  } finally {
    editDialog.loading = false
  }
}

// 删除文档
const handleDelete = async (row) => {
  try {
    await deleteDocument(row.doc_id)
    ElMessage.success('删除成功')
    fetchDocuments()
  } catch (error) {
    ElMessage.error('删除失败：' + error)
  }
}

// 工具函数
const isTextFile = (type) => {
  return ['txt', 'md', 'json', 'xml'].includes(type?.toLowerCase())
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) {
    bytes /= 1024
    i++
  }
  return bytes.toFixed(2) + ' ' + units[i]
}

const formatDate = (date) => {
  if (!date) return '-'
  const d = new Date(date)
  return d.toLocaleString('zh-CN')
}

const truncateId = (id) => {
  if (!id) return '-'
  return id.substring(0, 8) + '...'
}

const copyId = (id) => {
  navigator.clipboard.writeText(id).then(() => {
    ElMessage.success('已复制到剪贴板')
  })
}

const getStatusType = (status) => {
  const types = {
    'pending': 'info',
    'parsing': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status) => {
  const texts = {
    'pending': '待解析',
    'parsing': '解析中',
    'completed': '已解析',
    'failed': '解析失败'
  }
  return texts[status] || status
}

onMounted(() => {
  fetchDocuments()
})
</script>

<style scoped>
.document-manager {
  padding-bottom: 24px;
}

.operation-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.left-operations {
  display: flex;
  gap: 12px;
}

.document-table-card {
  margin-bottom: 20px;
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 10px;
}

.doc-icon {
  color: #667eea;
}

.doc-info {
  display: flex;
  flex-direction: column;
}

.doc-info .name {
  font-weight: 500;
  color: #333;
}

.doc-info .type {
  font-size: 12px;
  color: #999;
}

.doc-id {
  font-family: monospace;
  font-size: 13px;
  color: #666;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

:deep(.el-upload-dragger) {
  width: 100%;
}
</style>
