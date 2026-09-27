#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""classify_notes.py —— 把知识库根目录的 .md 笔记按关键词归入 10 个专题文件夹。

用法（Windows / Linux 通用，Python 3 标准库，无需第三方依赖）：

    # 预演，只打印计划，不动任何文件（默认）
    python3 classify_notes.py --root "D:\\AI云文档\\AI知识库\\AI学习知识库"

    # 确认结果后再实际移动
    python3 classify_notes.py --root "D:\\AI云文档\\AI知识库\\AI学习知识库" --apply

    # 同时把计划/报告写到文件
    python3 classify_notes.py --root "..." --report "D:\\...\\分类计划.md"

设计要点：
- 默认 dry-run，必须显式 --apply 才会移动文件（安全第一）。
- 只扫描 root 顶层的 *.md，不递归；专题/、meta/、归档/ 等子目录天然被忽略。
- 命中多个专题时按得分取最高，同分取编号小者；一个关键词命中一次计分。
- 无法归类的文件只列出来，交给人工处理，不做猜测性移动。
- 中文全程 UTF-8，避免 PowerShell 中文编码问题。
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

# 让 Windows 控制台也能输出中文（失败时静默降级）
try:  # pragma: no cover - 环境相关
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass


# 10 个专题：编号 -> (文件夹名, 关键词表)
TOPICS: dict[str, tuple[str, tuple[str, ...]]] = {
    "01": ("01-认知与学习科学", (
        "睡眠", "多巴胺", "元认知", "学习", "大脑", "N-Back", "嫉妒心",
        "记忆", "认知负荷", "专注", "注意", "情绪",
    )),
    "02": ("02-思维方法论", (
        "思维", "方法论", "第一性原理", "四把刀", "尼采", "失控", "园丁",
        "半控制", "外脑", "博弈", "决策", "哲学思维", "模型思维",
    )),
    "03": ("03-AI基础认知", (
        "大模型", "Token", "API", "MCP", "Skill", "提示词", "上下文",
        "幻觉", "微调", "RAG", "向量",
    )),
    "04": ("04-AI模型与行业趋势", (
        "DeepSeek", "OpenAI", "Claude", "Kimi", "就业", "淘汰", "创业",
        "周报", "算力", "行业趋势",
    )),
    "05": ("05-AI工具链", (
        "Hermes", "Ollama", "Agnes", "Trae", "NIM", "ComfyUI", "Jarvis",
        "Claude Code", "Edge-TTS", "HF-Mirror",
    )),
    "06": ("06-AI编程与开发", (
        "VS Code", "Python", "编程", "代码", "Agent开发", "Ponytail",
        "工作流", "调试", "Git",
    )),
    "07": ("07-知识管理与蒸馏", (
        "蒸馏", "知识库", "P.A.R.A", "笔记", "读书", "书籍", "喂饭级教程",
        "7层架构", "整理",
    )),
    "08": ("08-软件安装与排错", (
        "安装", "配置", "踩坑", "排错", "Chrome", "豆包", "浏览器",
        "后缀", "下载", "报错",
    )),
    "09": ("09-国学与人文思辨", (
        "道德经", "论语", "哲学", "历史", "文明", "周期", "蛊真人", "涌现",
        "国学",
    )),
    "10": ("10-AI Agent开发", (
        "Agent", "MCP", "CoT", "ReAct", "多智能体", "工具调用", "智能体",
    )),
}

# 顶层这些文件不参与归类
SKIP_EXACT = {
    "00-专题分类总览.md",
    "知识库合并版（AI引用专用）.md",
    "知识库合并版(AI引用专用).md",
    "_飞书备份.md",
    "README.md",
}
SKIP_PREFIX = ("00-", ".")

CONTENT_SAMPLE_CHARS = 2000
FILENAME_WEIGHT = 2
CONTENT_WEIGHT = 1


def score_text(text: str, weight: int) -> dict[str, int]:
    """给一段文本按关键词表打分。一个关键词在文本中出现一次计一次。"""
    scores: dict[str, int] = {}
    if not text:
        return scores
    lowered = text.lower()
    for topic_id, (_folder, keywords) in TOPICS.items():
        hits = 0
        for kw in keywords:
            if not kw:
                continue
            if kw.lower() in lowered:
                hits += 1
        if hits:
            scores[topic_id] = hits * weight
    return scores


def classify(path: Path) -> tuple[str | None, dict[str, int], str]:
    """返回 (专题编号 或 None, 得分明细, 说明)。"""
    scores = score_text(path.stem, FILENAME_WEIGHT)
    note = "按文件名命中"
    if not scores:
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:CONTENT_SAMPLE_CHARS]
        except OSError as exc:
            return None, {}, f"读取失败：{exc}"
        scores = score_text(head, CONTENT_WEIGHT)
        note = "按正文前 %d 字命中" % CONTENT_SAMPLE_CHARS
    if not scores:
        return None, {}, "无关键词命中"
    best = max(scores.items(), key=lambda kv: (kv[1], -int(kv[0])))
    return best[0], scores, note


def iter_candidates(root: Path) -> list[Path]:
    files = []
    for p in sorted(root.iterdir(), key=lambda x: x.name):
        if not p.is_file() or p.suffix.lower() != ".md":
            continue
        name = p.name
        if name in SKIP_EXACT or name.startswith(SKIP_PREFIX):
            continue
        files.append(p)
    return files


def unique_target(target: Path) -> Path:
    """目标已存在时加序号后缀，绝不覆盖。"""
    if not target.exists():
        return target
    stem, suffix = target.stem, target.suffix
    for i in range(2, 1000):
        candidate = target.with_name(f"{stem} ({i}){suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法为 {target} 找到可用文件名")


def build_plan(root: Path) -> tuple[list[dict], list[Path]]:
    plan: list[dict] = []
    unclassified: list[Path] = []
    topics_root = root / "专题"
    for src in iter_candidates(root):
        topic_id, scores, note = classify(src)
        if topic_id is None:
            unclassified.append(src)
            continue
        folder = TOPICS[topic_id][0]
        dst = topics_root / folder / src.name
        plan.append({
            "file": src.name,
            "topic": topic_id,
            "folder": folder,
            "target": str(dst),
            "scores": scores,
            "note": note,
        })
    return plan, unclassified


def render_report(root: Path, plan: list[dict], unclassified: list[Path], apply: bool) -> str:
    lines = []
    lines.append("# 知识库归类计划" + ("（已执行）" if apply else "（预演，未改动文件）"))
    lines.append("")
    lines.append(f"- 根目录：{root}")
    lines.append(f"- 待归类：{len(plan)} 个文件")
    lines.append(f"- 无法归类：{len(unclassified)} 个文件")
    lines.append("")
    if plan:
        lines.append("| 文件 | 专题 | 依据 |")
        lines.append("|------|------|------|")
        for item in plan:
            lines.append(f"| {item['file']} | {item['folder']} | {item['note']} |")
        lines.append("")
    if unclassified:
        lines.append("## 无法归类（请人工处理，不会自动移动）")
        lines.append("")
        for p in unclassified:
            lines.append(f"- {p.name}")
        lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="把知识库根目录的 .md 笔记按关键词归入 10 个专题文件夹（默认 dry-run）",
    )
    parser.add_argument("--root", required=True, help="本地知识库根目录，例如 D:\\AI云文档\\AI知识库\\AI学习知识库")
    parser.add_argument("--dry-run", action="store_true",
                        help="显式声明预演；本脚本默认就是预演，此参数只为与文档写法一致")
    parser.add_argument("--apply", action="store_true", help="实际移动文件；不加此参数只预演")
    parser.add_argument("--report", help="把计划/报告写入指定文件（.md 或 .txt）")
    parser.add_argument("--json", action="store_true", help="以 JSON 输出到标准输出，便于程序消费")
    args = parser.parse_args(argv)

    root = Path(args.root).expanduser()
    if not root.is_dir():
        print(f"[错误] 根目录不存在或不是目录：{root}", file=sys.stderr)
        return 2

    topics_root = root / "专题"
    if not topics_root.is_dir():
        print(f"[警告] 未找到专题目录：{topics_root}（--apply 时将自动创建）", file=sys.stderr)

    plan, unclassified = build_plan(root)

    moved, failed = [], []
    if args.apply:
        for item in plan:
            src = root / item["file"]
            target = Path(item["target"])
            try:
                target.parent.mkdir(parents=True, exist_ok=True)
                target = unique_target(target)
                shutil.move(str(src), str(target))
                item["target"] = str(target)
                moved.append(item)
            except Exception as exc:  # noqa: BLE001 - 逐文件容错
                failed.append({"file": item["file"], "error": str(exc)})
                print(f"[失败] {item['file']} -> {target}：{exc}", file=sys.stderr)

    report = render_report(root, plan, unclassified, args.apply)

    if args.json:
        print(json.dumps({
            "root": str(root),
            "applied": bool(args.apply),
            "planned": plan,
            "unclassified": [p.name for p in unclassified],
            "moved": [m["file"] for m in moved],
            "failed": failed,
        }, ensure_ascii=False, indent=2))
    else:
        print(report)
        if args.apply:
            print(f"[完成] 已移动 {len(moved)} 个文件，失败 {len(failed)} 个。")
        else:
            print("[预演结束] 未改动任何文件；确认无误后加 --apply 执行。")

    if args.report:
        Path(args.report).write_text(report, encoding="utf-8")
        print(f"[报告] 已写入 {args.report}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
