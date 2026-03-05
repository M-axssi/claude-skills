# 追踪新论文

追踪某个研究方向自上次查询以来的新论文，并保存到本地索引。

**用法：** `/track-papers <研究方向>`

**示例：** `/track-papers 3D模型生成`

---

## 执行步骤

你是一个帮助计算机图形学博士追踪最新论文的助手。所有输出请使用**中文**。

要追踪的方向：**$ARGUMENTS**

### 第一步：读取上次查询时间

读取文件 `D:/claude_tools/paper_search/paper_tracker_state.json`。

- 若文件不存在，将上次查询时间视为今天往前6个月。
- 对方向名称进行模糊匹配（如"3D模型生成"和"3D model generation"视为同一方向）。
- 若该方向不存在记录，同样视为6个月前。

记录上次查询日期为 `last_date`（格式 YYYY-MM-DD）。

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

合并4轮结果，过滤出发布/上传时间晚于 `last_date` 的论文，以标题去重，候选集最多40篇。

### 第三步：排序筛选

按以下优先级排序：
1. **与方向的相关性**（首要）
2. **影响力**（次要）——优先顶会（SIGGRAPH、CVPR、ICCV、NeurIPS、ECCV、ACM TOG）及引用数高的论文
3. arXiv 预印本与已发表论文同等对待

最多选出 **20篇**。

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

### 第五步：保存到索引

读取 `D:/claude_tools/paper_search/papers_db.json`（不存在则创建）。

将每篇论文添加到对应方向的列表中，以标题去重，避免重复。

papers_db.json 格式：
```json
{
  "方向名称": [
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
  ]
}
```

将更新后的 JSON 写回 `D:/claude_tools/paper_search/papers_db.json`。

### 第六步：更新查询时间

更新 `D:/claude_tools/paper_search/paper_tracker_state.json`：
- 将 **$ARGUMENTS** 的最后查询时间设为今天（YYYY-MM-DD 格式）
- 保留文件中其他方向的记录

格式：
```json
{
  "方向名称": "YYYY-MM-DD"
}
```

最后告知用户：找到了几篇论文（arXiv/Scholar 各几篇），索引已更新，可以用 `/list-papers` 查看所有已保存的论文。
