# 追踪新论文

追踪某个研究方向自上次查询以来的新论文，并保存到本地索引。

**用法：** `/track-papers <研究方向>`

**示例：** `/track-papers 3D模型生成`

---

## 执行步骤

你是一个帮助计算机图形学博士追踪最新论文的助手。所有输出请使用**中文**。

要追踪的方向：**$ARGUMENTS**

### 第一步：读取搜索上下文（Python 脚本，零 token）

```bash
python D:/claude-skills/paper_search/papers_cli.py context --direction "$ARGUMENTS"
```

脚本输出 JSON，包含：
- `last_date`：上次查询日期（若无记录则为6个月前）
- `existing_titles`：该方向已有论文标题列表（用于后续去重）

记录 `last_date` 和 `existing_titles` 供后续步骤使用。

### 第二步：双源搜索新论文

同时使用 **arXiv MCP** 和 **Google Scholar MCP** 搜索，以获得最全面的覆盖。

**arXiv 搜索（优先，获取最新预印本）：**

根据方向选择合适的 arXiv 分类：
- 3D生成、渲染、几何处理 → categories: `["cs.GR", "cs.CV"]`
- 扩散模型、生成模型 → categories: `["cs.CV", "cs.LG"]`
- 点云、重建 → categories: `["cs.GR", "cs.CV"]`
- 通用 CG/CV 方向 → categories: `["cs.GR", "cs.CV"]`

执行以下搜索：
1. 用 `search_papers`，query 为方向的英文关键词，date_from 设为 `last_date`，categories 设为上述分类，max_results=20
2. 用 `search_papers`，换一组近义关键词，同样 date_from 和 categories，max_results=15

**Google Scholar 搜索（补充，获取已发表论文）：**

3. 用 `search_google_scholar_advanced`，query 为方向关键词，year_range 设为上次查询年份到今年，num_results=10
4. 用 `search_google_scholar_advanced`，结合顶会词如 "SIGGRAPH CVPR ICCV"，num_results=10

合并4轮搜索结果为一个 JSON，调用 Python 脚本完成日期过滤、去重、质量筛选、排序（零 LLM token）：

```bash
echo '{
  "papers": [ <合并后的所有搜索结果> ],
  "existing_titles": [ <第一步获得的 existing_titles> ],
  "date_from": "<第一步获得的 last_date>",
  "max_results": 20
}' | python D:/claude-skills/paper_search/filter_papers.py
```

脚本输出：
- `filtered`：已去重、日期过滤、质量筛选、排好序的论文列表
- `needs_author_check`：arXiv 论文中机构无法确认的部分
- `stats`：各阶段计数

### 第三步：补充 get_author_info（仅针对 needs_author_check）

对脚本输出的 `needs_author_check` 列表，调用 `get_author_info` 查询通讯作者：
- h-index ≥ 20，或总引用数 ≥ 1000 → 加入最终列表末尾
- 否则丢弃

> 注：get_author_info 若超过 1 分钟未返回，改用 WebSearch 搜索「<作者名> Google Scholar」判断；若仍无法确认，直接丢弃。

### 第四步：展示结果

以如下格式输出中文报告：

```
## 新论文追踪：<方向>
**周期：** <上次查询日期> → <今天>
**发现：** <N> 篇新论文（arXiv: X篇 | Google Scholar: Y篇）

---

1. **<标题>**
   - 作者：<作者1>，<作者2>，...
   - 日期：<YYYY-MM>
   - 发表于：<会议/期刊，或 arXiv:XXXX.XXXXX>
   - 摘要：<一句话概括核心贡献>

2. ...
```

若没有发现新论文，清晰说明。

### 第五步：保存到索引并更新追踪时间（Python 脚本，零 token）

将最终论文列表（`filtered` + 通过 get_author_info 验证的论文）通过 Bash 传给脚本，脚本自动去重、写入数据库、更新追踪时间：

```bash
echo '[ <最终论文列表 JSON 数组> ]' | python D:/claude-skills/paper_search/papers_cli.py save --direction "$ARGUMENTS" --type track
```

papers_db.json 中每篇论文的格式：
```json
{
  "title": "论文标题",
  "authors": ["作者1", "作者2"],
  "date": "YYYY-MM",
  "venue": "SIGGRAPH 2025",
  "summary": "一句话摘要。",
  "found_at": "YYYY-MM-DD",
  "type": "track",
  "source": "arxiv 或 google_scholar",
  "arxiv_id": "XXXX.XXXXX（若来自arXiv）"
}
```

脚本会同时更新 `paper_tracker_state.json` 的最后查询时间为今天。

最后告知用户：找到了几篇新论文，索引已更新，可以用 `/list-papers` 查看所有已保存的论文。
