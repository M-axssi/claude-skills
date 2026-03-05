# 搜索重要论文

搜索某个研究方向近5年内的重要论文，按影响力排序。

**用法：** `/survey-papers <研究方向>`

**示例：** `/survey-papers 神经辐射场`

---

## 执行步骤

你是一个帮助计算机图形学博士调研重要论文的助手。所有输出请使用**中文**。

要调研的方向：**$ARGUMENTS**

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

合并所有结果，以标题去重，候选集最多50篇。

### 第二步：排序筛选

将所有结果按以下标准排序：
1. **综述/Survey 论文**优先排在最前面
2. **引用数**（由高到低，Google Scholar 来源有引用数优先参考）
3. **顶会论文**（SIGGRAPH、CVPR、ICCV、NeurIPS、ECCV、ACM TOG）优先
4. arXiv 高引用预印本与已发表论文同等对待

最多选出 **20篇**。

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

### 第四步：保存到索引

读取 `D:/claude_tools/paper_search/papers_db.json`（不存在则创建）。

将每篇论文添加到对应方向的列表中，以标题去重。type 字段设为 `"survey"`。

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
      "type": "survey",
      "source": "arxiv 或 google_scholar",
      "arxiv_id": "XXXX.XXXXX（若来自arXiv）"
    }
  ]
}
```

将更新后的 JSON 写回 `D:/claude_tools/paper_search/papers_db.json`。

最后告知用户：找到了几篇论文（arXiv/Scholar 各几篇），索引已更新，可以用 `/list-papers` 查看所有已保存的论文。
