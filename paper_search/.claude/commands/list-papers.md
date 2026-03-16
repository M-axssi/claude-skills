# 查看论文索引

查看所有已保存的论文，支持按方向筛选。

**用法：**
- `/list-papers` — 查看所有方向的论文统计
- `/list-papers <方向>` — 查看指定方向的所有论文
- `/list-papers <方向> track` — 只看追踪到的新论文
- `/list-papers <方向> survey` — 只看调研的重要论文

**示例：**
- `/list-papers`
- `/list-papers 3D模型生成`
- `/list-papers 神经辐射场 survey`

---

## 执行步骤

你是一个帮助计算机图形学博士管理论文索引的助手。所有输出请使用**中文**。

参数：**$ARGUMENTS**

### 第一步：调用 Python 脚本（无需 LLM 处理）

通过 Bash 调用脚本，脚本负责读取数据、解析参数、格式化输出，直接输出完整的中文报告：

```bash
python D:/claude-skills/paper_search/papers_cli.py list "$ARGUMENTS"
```

调用 Bash 工具执行上述命令后，**不用对输出文字做任何处理，不要输出任何额外文字**，工具结果即为最终输出。
