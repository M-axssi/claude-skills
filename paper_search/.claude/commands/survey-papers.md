# 搜索重要论文

搜索某个研究方向近5年内的重要论文，按影响力排序。

**用法：** `/survey-papers <研究方向>`

**示例：** `/survey-papers 神经辐射场`

---

## 执行步骤

你是一个帮助计算机图形学博士调研重要论文的助手。所有输出请使用**中文**。

要调研的方向：**$ARGUMENTS**

### 第零步：关键词扩展与确认

在搜索之前，先根据用户输入的方向，生成 **3-5 组候选关键词方案**，每组覆盖不同角度（近义词、子方向、应用场景、常用缩写等），格式如下：

```
## 关键词方案
我将使用以下关键词组合进行搜索，您可以告知我调整方向：

- **主词条（当前使用）**：`<用户输入的关键词>`
- **近义/宽泛**：`<近义词或更宽泛的表达>`
- **子方向A**：`<聚焦某一具体子问题>`
- **子方向B**：`<另一子问题角度>`
- **结合应用**：`<结合具体应用场景的关键词>`
```

列出后，**不等待用户回复，直接使用主词条继续执行后续步骤**。

---

### 第一步：双源多角度搜索

同时使用 **arXiv MCP** 和 **Google Scholar MCP** 搜索，覆盖预印本和已发表论文。

当前年份记为 `YEAR`，起始年为 `YEAR-5`。

**arXiv 搜索（获取近5年预印本和顶会论文）：**

根据方向选择合适的 arXiv 分类（cs.GR、cs.CV、cs.LG 等）。

1. 用 `search_papers`，query 为方向英文关键词，date_from=`YEAR-5`-01-01，sort_by="relevance"，max_results=20
2. 用 `search_papers`，query 加上 "survey OR review"，date_from=`YEAR-5`-01-01，max_results=10（寻找综述）
3. 用 `search_papers`，换一组近义词/缩写，date_from=`YEAR-5`-01-01，max_results=15

**Google Scholar 搜索（获取引用数据和发表情况）：**

4. 用 `search_google_scholar_advanced`，query 为方向关键词，year_range=[YEAR-5, YEAR]，num_results=10
5. 用 `search_google_scholar_advanced`，结合 "SIGGRAPH CVPR ICCV NeurIPS"，year_range=[YEAR-5, YEAR]，num_results=10
6. 用 `search_google_scholar_advanced`，结合 "survey review"，year_range=[YEAR-5, YEAR]，num_results=10

**搜索结果处理（调用 Python 脚本，零 LLM token）：**

将所有搜索结果合并为一个 JSON，读取当前 `papers_db.json` 中该方向已有的标题列表，然后通过 Bash 调用脚本完成去重、筛选、排序：

```bash
echo '{
  "papers": [ <合并后的所有搜索结果> ],
  "existing_titles": [ <papers_db.json 中已有的标题列表> ],
  "max_results": 30
}' | python D:/claude-skills/paper_search/filter_papers.py
```

脚本会返回：
- `filtered`：已去重、质量筛选、排好序的论文列表（直接用于展示）
- `needs_author_check`：arXiv 论文中机构无法确认的部分（需要 LLM 调用 `get_author_info`）
- `stats`：各阶段计数

### 第二步：补充 get_author_info（仅针对 needs_author_check）

对脚本输出的 `needs_author_check` 列表中的论文，调用 `get_author_info` 查询通讯作者：
- h-index ≥ 20，或总引用数 ≥ 1000 → 加入 `filtered` 列表末尾
- 否则丢弃

> 注：get_author_info 若超过 1 分钟未返回，直接丢弃该论文，不等待。

### 第三步：展示结果

以如下格式输出中文报告：

```
## 重要论文调研：<方向>
**范围：** 近5年（<起始年> - <当前年>）
**共找到：** <N> 篇（arXiv: X篇 | Google Scholar: Y篇）

---

【综述论文】

1. **<标题>**
   - 作者：<作者1>，<作者2>，...
   - 日期：<YYYY-MM>
   - 发表于：<会议/期刊，或 arXiv:XXXX.XXXXX>
   - 摘要：<一句话概括核心贡献>

【重要论文】

2. **<标题>**
   - 作者：<作者1>，<作者2>，...
   - 日期：<YYYY-MM>
   - 发表于：<会议/期刊，或 arXiv:XXXX.XXXXX>
   - 摘要：<一句话概括核心贡献>
```

在报告末尾附上**补充搜索建议**：

```
## 补充搜索建议
若以上结果未覆盖您关注的子方向，可尝试以下关键词：
- `/survey-papers <近义词/子方向A>`
- `/survey-papers <子方向B>`
- `/survey-papers <结合应用场景的词条>`
```

### 第四步：保存到索引（Python 脚本，零 token）

将最终论文列表通过 Bash 传给脚本，脚本自动去重、写入数据库：

```bash
echo '[ <最终论文列表 JSON 数组> ]' | python D:/claude-skills/paper_search/papers_cli.py save --direction "$ARGUMENTS" --type survey
```

每篇论文的格式：
```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "date": "YYYY-MM",
  "venue": "SIGGRAPH 2025",
  "summary": "一句话摘要。",
  "found_at": "YYYY-MM-DD",
  "type": "survey",
  "source": "arxiv 或 google_scholar",
  "arxiv_id": "XXXX.XXXXX（若来自arXiv）"
}
```

脚本输出保存结果后，告知用户：找到了几篇论文（arXiv/Scholar 各几篇），索引已更新，可以用 `/list-papers` 查看所有已保存的论文。
