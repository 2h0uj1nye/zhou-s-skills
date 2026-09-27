# 飞书同步：配置、命令与失败处理

本文件是 `kb-sync` 第 5 步的细则。

> ⚠️ **本文件及整个技能包内不得出现任何真实空间 ID、node token、doc token。**
> 所有目标标识一律从本机配置文件 `D:\AI云文档\AI知识库\config\kb-targets.json` 读取。
> 该配置**不进技能包、不随包分享**。

## 1. 配置文件结构（kb-targets.json）

本机需要存在这样一份配置（值为占位符，实际值只写在你的 Windows 机器上）：

```json
{
  "space_id": "<AI学习知识库空间ID>",
  "nodes": {
    "merged_file":  { "label": "合并版",            "node": "<node_token>", "doc": "<doc_id>" },
    "faq_thinking": { "label": "FAQ-思维方法论",    "node": "<node_token>", "doc": "<doc_id>" },
    "faq_software": { "label": "FAQ-软件下载安装",  "node": "<node_token>", "doc": "<doc_id>" },
    "faq_program":  { "label": "FAQ-编程工具使用",  "node": "<node_token>", "doc": "<doc_id>" }
  },
  "topic_nodes": {
    "01": { "label": "01-认知与学习科学专题", "node": "<node_token>" },
    "02": { "label": "02-思维方法论专题",     "node": "<node_token>" },
    "03": { "label": "03-AI基础认知专题",     "node": "<node_token>" },
    "04": { "label": "04-AI模型与行业趋势专题", "node": "<node_token>" },
    "05": { "label": "05-AI工具链专题",       "node": "<node_token>" },
    "06": { "label": "06-AI编程与开发专题",   "node": "<node_token>" },
    "07": { "label": "07-知识管理与蒸馏专题", "node": "<node_token>" },
    "08": { "label": "08-软件安装与排错专题", "node": "<node_token>" },
    "09": { "label": "09-国学与人文思辨专题", "node": "<node_token>" },
    "10": { "label": "10-AI Agent开发专题",   "node": "<node_token>" }
  }
}
```

**读取方式**：

```powershell
# 只读配置，不打印全部内容（避免 token 进入日志/回显）
$cfg = Get-Content "D:\AI云文档\AI知识库\config\kb-targets.json" -Raw -Encoding UTF8 | ConvertFrom-Json
$cfg.nodes.merged_file.node      # 合并版节点
$cfg.nodes.faq_thinking.doc      # FAQ 文档 ID
```

- 配置缺失 / JSON 解析失败 → **停等用户补齐**，不要凭记忆或旧会话猜 node。
- 读取凭据时**不要整段回显**到对话或日志中。

## 2. 上传命令（外部脚本 `upload_to_feishu.py`）

> 这是**外部运行环境依赖**，位于 `D:\AI云文档\AI知识库\scripts\`，不在本技能包内。
> Windows 上无 `lark-cli`，一律用这个脚本。

```powershell
# 1. 新建笔记节点 + 写入内容（脚本会复用同名节点，不会重复创建）
python "D:\AI云文档\AI知识库\scripts\upload_to_feishu.py" new `
  "D:\AI云文档\AI知识库\AI学习知识库\专题\02-思维方法论专题\笔记1.md" `
  "D:\AI云文档\AI知识库\AI学习知识库\专题\02-思维方法论专题\笔记2.md"

# 2. 覆盖更新已有节点（合并版 / FAQ）
#    --node / --doc 的值从 kb-targets.json 读取，不要写死在这里
python "D:\AI云文档\AI知识库\scripts\upload_to_feishu.py" overwrite `
  --node $cfg.nodes.merged_file.node --doc $cfg.nodes.merged_file.doc `
  "D:\AI云文档\AI知识库\AI学习知识库\07-知识管理与蒸馏\知识库合并版（AI引用专用）.md"

# 3. 列出空间所有节点（用于确认节点是否存在 / 找 token）
python "D:\AI云文档\AI知识库\scripts\upload_to_feishu.py" list
```

要点：

- `new` 可一次传多个文件（已验证 11 个文件一次成功）。
- FAQ 更新 = 用 `overwrite` 覆盖**整个** FAQ 文档（本地文件已是全量）。
- **每次 `overwrite` 前先 `list` 确认节点真实存在**，不要直接使用记忆里的旧 token。
- 脚本只读本地文件、只写远端，**不修改本地**；本地变更走本地写入流程。

## 3. 失败处理

| 失败现象 | 原因 | 退路 |
|----------|------|------|
| token 过期 | 飞书 token 约 2 小时有效期 | 由 `feishu-api.ps1` / 脚本自动刷新；仍失败 → 请用户重新授权 |
| 节点 ID 失效 | 节点被删除或重建 | 先 `list` 取实际存在的 node，再 overwrite |
| `1770001 invalid param`（批量删除） | batch_delete 用固定 start/end 索引，删除后错位 | 脚本已内置：`start_index=0`，`step=min(50, remaining)` |
| 节点重复创建 | 同名节点查询只翻第一页 | 脚本 `find_node` 已翻页；先 `list` 确认再建 |
| **上传脚本缺失** | 外部依赖未安装 / 路径变更 | **本地照常完成第 3–4 步并写 ops-log**；告知用户"飞书未同步"及缺失路径；**不得伪造上传成功** |
| 上传超时 / 网络中断 | 网络问题 | 重试一次；仍失败则记录 `error` 到 ops-log，改为下次补传，本地结果不回滚 |

## 4. 飞书 API 的硬限制（必须知道）

- 飞书 Wiki API **不支持直接移动 / 重分类文档**。
- 只能"删除旧节点 + 创建新节点"实现移动，**风险高**（会丢历史、丢权限、丢链接）。
- **推荐做法**：本地与飞书**分别维护**，靠 `new` / `overwrite` 保持内容一致即可，不追求两边目录结构完全镜像。
- 因此"把飞书里的文档挪到另一个专题"**不是本技能的职责**；用户提出时先说明该限制。

## 5. 并发与串行

- 节点创建 + 内容写入：不同文档**可并行**
- FAQ 更新、合并版更新：**必须串行**（先本地改完，再 overwrite）
- 本地写入（第 3 步）与蒸馏输出（第 2 步）可同步进行
