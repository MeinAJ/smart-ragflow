# DeepDocParser 核心流程分析

## 概述

`DeepDocParser` 是一个基于 DeepDoc 的文档解析模块，支持 PDF、Word、TXT、Markdown、HTML 等多种格式。核心设计思想是：**统一入口 + 格式特化解析 + 通用结构提取**。

---

## 核心架构

```
parse(file_path) ──┬──> _parse_pdf()   ──┐
                   ├──> _parse_word()  ──┤
                   ├──> _parse_txt()   ──┼──> _parse_structure() ──> Document ──> ParseResult
                   ├──> _parse_md()    ──┤        (统一结构解析)
                   └──> _parse_html()  ──┘
```

---

## 各解析方法详细分析

### 1. `_parse_pdf(file_path)` - PDF 解析

**依赖库**: `pdfplumber`

**核心流程**:
```
1. 尝试导入 pdfplumber（未安装则返回 mock 结果）
2. 使用 pdfplumber.open() 打开 PDF
3. 遍历每一页 (enumerate(pdf.pages, 1))
   ├── 调用 page.extract_text() 提取文本
   ├── 将文本加入 text_parts 列表
   └── 创建 DocumentElement 对象（记录页码）
4. 合并所有文本 → full_text
5. 调用 _parse_structure(full_text) 解析章节结构
6. 更新各章节的起止页码
7. 构建 Document 对象并返回 ParseResult
```

**关键特点**:
- 支持分页信息提取（page_number）
- 每个段落作为一个 DocumentElement
- 章节页码统一设置为文档的起止范围

---

### 2. `_parse_word(file_path)` - Word 解析

**依赖库**: `python-docx`

**核心流程**:
```
1. 尝试导入 docx（未安装则返回 mock 结果）
2. 使用 docx.Document() 加载文件
3. 遍历文档所有段落 (doc.paragraphs)
   ├── 跳过空段落
   ├── 判断段落样式：style.name.startswith("Heading") 则为标题
   └── 创建 DocumentElement（标记 element_type: "paragraph"/"title"）
4. 合并所有段落文本
5. 调用 _parse_structure() 解析章节结构
6. 提取文档元数据（author, created 等）
7. 构建 Document 对象并返回 ParseResult
```

**关键特点**:
- 支持标题样式识别（Heading 样式）
- 提取 Word 文档属性作为元数据
- 无需处理页码（设为 0）

---

### 3. `_parse_txt(file_path)` - 纯文本解析

**核心流程**:
```
1. 以 UTF-8 编码打开文件读取全部内容
2. 调用 _parse_structure(text) 解析章节结构
3. 构建 Document 对象并返回 ParseResult
```

**关键特点**:
- 最简单的解析方式，直接读取文本
- 结构解析完全依赖 _parse_structure 的正则匹配
- 无依赖库要求

---

### 4. `_parse_md(file_path)` - Markdown 解析

**实现方式**:
```python
def _parse_md(self, file_path: Path) -> ParseResult:
    return self._parse_txt(file_path)  # Markdown 也是文本格式
```

**关键特点**:
- 直接复用 `_parse_txt()` 方法
- Markdown 的标题标记（# ## ###）会被 `_parse_structure()` 正确识别
- 无需额外处理

---

### 5. `_parse_html(file_path)` - HTML 解析

**依赖库**: `beautifulsoup4`

**核心流程**:
```
1. 尝试导入 BeautifulSoup（未安装则降级为 _parse_txt）
2. 读取文件内容并创建 BeautifulSoup 对象
3. 清理无用标签：
   └── 移除所有 <script> 和 <style> 标签（decompose）
4. 提取纯文本：soup.get_text()
5. 清理空白字符：
   ├── 按行分割并去除每行首尾空白
   ├── 按双空格分割并去除短语首尾空白
   └── 过滤空行，重新合并为规范文本
6. 调用 _parse_structure() 解析章节结构
7. 尝试提取 HTML <title> 作为文档标题
8. 构建 Document 对象并返回 ParseResult
```

**关键特点**:
- 去除脚本和样式干扰
- 智能清理空白字符，保留文本结构
- 支持提取 HTML 页面标题

---

## 通用结构解析：`_parse_structure(text)`

这是所有解析方法共享的核心方法，负责从纯文本中提取章节层级结构。

**核心流程**:
```
1. 初始化：sections = [], current_section = None, current_content = []
2. 编译正则表达式：^(#{1,6})\s+(.+)$ （匹配 1-6 级 Markdown 标题）
3. 逐行遍历文本：
   ├── 匹配到标题行
   │   ├── 保存上一个章节到 sections
   │   ├── 创建新 DocumentSection（level = # 数量, title = 标题内容）
   │   └── 重置 current_content
   └── 非标题行
       ├── 如果已有当前章节：追加到 current_content
       └── 如果无当前章节（前言部分）：创建 level=0 的无标题章节
4. 保存最后一个章节
5. 兜底处理：如果没有任何章节，将整个文本作为一个 level=1 的章节
6. 返回 sections 列表
```

**标题识别规则**:
| 标记 | Level | 含义 |
|------|-------|------|
| `# 标题` | 1 | 一级标题（文档主标题） |
| `## 标题` | 2 | 二级标题 |
| `### 标题` | 3 | 三级标题 |
| ... | ... | ... |
| `###### 标题` | 6 | 六级标题 |

---

## 文档标题提取：`_extract_title(text)`

**逻辑**: 取文本第一行非空且长度小于 200 字符的内容作为标题

```python
def _extract_title(self, text: str) -> str:
    lines = text.strip().split("\n")
    for line in lines:
        line = line.strip()
        if line and len(line) < 200:
            return line
    return "Untitled"
```

---

## 容错机制：`_create_mock_result(file_path)`

当依赖库未安装或解析异常时，返回模拟结果以确保接口兼容性：

```
创建 Document 对象：
- title: 文件名（不含扩展名）
- content: "Mock content for {filename}"
- sections: 单章节，标题为文件名
- 其他字段使用文件实际信息
```

---

## 数据模型

### Document
| 字段 | 说明 |
|------|------|
| title | 文档标题 |
| file_name | 原始文件名 |
| file_type | 文件类型 |
| file_path | 完整路径 |
| file_size | 文件大小 |
| content | 完整文本内容 |
| sections | 章节列表（List[DocumentSection]） |
| elements | 元素列表（List[DocumentElement]） |
| metadata | 元数据字典 |
| parsed_at | 解析时间 |

### DocumentSection
| 字段 | 说明 |
|------|------|
| title | 章节标题 |
| level | 层级（0-6） |
| content | 章节内容 |
| start_page | 起始页码 |
| end_page | 结束页码 |

### DocumentElement
| 字段 | 说明 |
|------|------|
| element_type | 元素类型（paragraph/title/table等） |
| content | 元素内容 |
| page_number | 所在页码 |

---

## 总结

| 格式 | 核心依赖 | 特殊处理 | 结构支持 |
|------|----------|----------|----------|
| PDF | pdfplumber | 分页提取 | 页码信息 |
| Word | python-docx | 样式识别、元数据提取 | 标题样式 |
| TXT | 无 | 直接读取 | Markdown 标题语法 |
| Markdown | 无 | 复用 TXT 解析 | Markdown 标题语法 |
| HTML | beautifulsoup4 | 标签清理、空白规范化 | Markdown 标题语法 |

**设计亮点**:
1. **统一接口**: 所有格式都返回 `ParseResult`，上层调用无需关心格式差异
2. **降级策略**: 依赖缺失时返回 mock 结果，保证系统可用性
3. **通用结构解析**: `_parse_structure()` 统一处理标题层级，支持 Markdown 语法
4. **丰富的元数据**: 提取文件属性、页码、作者等信息
