---
name: pdf-paper-notes-zh
description: Use when reading an AI4Science / algorithm-tool scientific PDF paper (a paper that PROPOSES a new model, method, pipeline, or computational tool — e.g. scGPT, Geneformer, COMPASS, AlphaFold, foundation models for biology/chemistry, deep-learning pipelines for genomics/protein/clinical data, ML methods for drug discovery, etc.) and needing to produce a Chinese literature reading note with original figures embedded. The 12-section template (model training, loss function, multimodal fusion, performance comparison) is engineered for this kind of paper. Triggers on requests like "读这篇 PDF 写文献阅读笔记", "整理这篇 paper 成图文笔记", "summarize this paper with figures" — but ONLY when the paper is a methods/algorithms paper, NOT a pure wet-lab or observational study.
---

# PDF 文献阅读笔记（中文图文版，AI4Science / 算法工具类）

## Overview

把一篇 **AI4Science / 算法工具类**科研 PDF 论文（提出新模型、新方法、新计算工具的论文）转化成**图文并茂的中文文献阅读笔记**，输出一个自包含目录：md 源文件 + html 渲染版 + figures + css。

核心原则：
1. **保留原文 figure**：直接从 PDF 中按 figure 提取图像，而非整页截图。
2. **结构化学术笔记**：12 个固定章节，覆盖总结、相关工作、创新点、技术细节、数据、训练、损失、对比等——专为"有模型、有训练、有损失"的算法论文设计；**强化学习论文额外追加一节 Reward Function**（见下）。
3. **图文对应**：每个关键章节嵌入对应 figure，配中文图注。
4. **可独立分发**：单一文件夹即可在浏览器中查看，无需额外依赖。

## When to Use

✅ **适用（AI4Science / 算法工具类论文）**：
- 论文**提出一个新模型/算法/计算工具**：foundation models for biology（scGPT、Geneformer、scFoundation）、结构预测（AlphaFold、ESMFold）、分子生成（DiffDock）、临床表型预测（COMPASS）、影像组学深度学习模型、单细胞/空间组学 pipeline、药物发现 ML 方法等
- 论文有明确的 **model architecture / training objective / loss function / benchmark** 描述
- 论文是 *Nature Methods* / *Nature Biotechnology* / *Nature Machine Intelligence* / *Cell Systems* / *Briefings in Bioinformatics* / NeurIPS / ICML / ICLR 等方法学/计算类期刊会议
- 用户给一篇上述类型的 PDF 并要求"写文献阅读笔记"/"图文并茂地介绍"/"扮演算法工程师视角分析"

⚠️ **慎用（需要在套模板前先判断）**：
- 混合型论文（方法 + 生物发现）：可用，但"损失函数""训练超参数"等章节只覆盖方法学部分，生物发现部分可适当扩展到"关键试验结果"章节
- 综述/ perspective 文章：模板的 12 章节不适用，建议直接摘要

❌ **不适用（明确不要触发本 skill）**：
- **纯湿实验/观察性生物学论文**（如临床队列免疫学、RCT、机制性 wet-lab 研究）：这些论文没有"模型训练""损失函数""超参数"，套模板会显得别扭、不准确。改为直接写摘要或使用其他笔记结构（推荐结构：背景 → 假设 → 实验设计 → 关键发现 → 机制阐释 → 临床/科学意义 → 局限）。
- 单纯问论文某一段是什么意思 → 直接回答
- 用户只想要一句话摘要 → 直接回答
- 用户明确要求纯文本摘要不要图 → 不要走本 skill

**判断口诀：论文里有没有 "model" / "training" / "loss" / "architecture" / "benchmark" 这些词的核心用法？有 → 用本 skill；没有 → 改用湿实验笔记结构。**

## Output Structure（强制约定）

直接在 **PDF 文件所在目录** 创建笔记文件夹，按 PDF 文件名命名子文件夹。**原始 PDF 文件会被移动（`mv`）到该文件夹中**（原位置不再保留，不是复制），确保 PDF 和笔记在一起：

```
<pdf-parent-dir>/
└── <pdf-filename-no-extension>/          # 笔记文件夹（在原 PDF 所在目录）
    ├── <pdf-filename-no-extension>.pdf   # 原始 PDF（已从原位置移动至此）
    ├── <Topic>_文献阅读笔记.md            # Markdown 源文件
    ├── <Topic>_文献阅读笔记.html          # HTML 版本（pandoc + MathJax + CSS）
    ├── style.css                         # 自定义 CSS（首次生成时复制）
    └── figures/                          # 从 PDF 提取的图片
        ├── Figure1_xxx.png
        ├── Figure2_xxx.png
        └── ...
```

**命名规则：**
- 子文件夹名 = PDF 文件名（去掉 .pdf 后缀），位于 PDF 所在目录
- PDF = 原始 PDF 文件**移动**（`mv`）到笔记文件夹，原位置不再保留（不是 cp）
- md/html 文件名 = `{主题中文}_文献阅读笔记` （如 `COMPASS_文献阅读笔记`）
- figure 文件名 = `Figure{N}_{english_slug}.png`（如 `Figure3_cross_generalization.png`）

## Workflow

```
1. 提取 PDF 文本        → pdftotext / PyMuPDF
2. 通读关键章节         → Abstract / Results / Methods / Discussion
3. 定位核心 figure      → 识别 Fig 1/2/3... 所在页码
4. 提取 figure 图像     → scripts/extract_figs.py（已知问题见下）
5. 写 Markdown 笔记     → 按 12 章节模板（若是 RL 论文，追加 Reward Function 章节，见下）
6. 生成 HTML            → pandoc + MathJax + style.css
7. 判断是否强化学习论文 → 关键词信号见「强化学习论文的额外处理」
8. 验证目录结构         → 所有文件路径正确、md/html/figures 齐全
9. 移动 PDF 到笔记文件夹 → mv <pdf_path> <note-dir>/<pdf-name>.pdf（放最后：确保笔记已成功生成后再移走原 PDF）
```

## 笔记 12 章节模板

每篇笔记必须按以下 12 个章节组织（详细模板见 `templates/notes_template.md`）：

1. 论文核心内容总结
2. 相关工作（Related Works）
3. 现有方法的不足
4. 核心创新点（最后需一句话概括）
5. 关键试验结果
6. 科学意义与应用价值
7. **文章的技术细节**（用户最关心，加重篇幅）
8. 模型训练的数据组成和来源（数据结构、模态）
9. 多模态数据融合策略（如适用）
10. 性能对比（指标 + 计算方法）
11. 训练策略与超参数
12. 损失函数
13. （⚠️ 仅强化学习论文）奖励函数 Reward Function —— 见下「强化学习论文的额外处理」

**写作风格要求：**
- 全程中文（CLAUDE.md 全局规则）；代码注释中文短句，log/print 英文
- 学术语言风格
- 数学抽象处配举例（如 "举例：假设基因 TP53 表达 TPM=120..."）
- 每个关键章节嵌入对应 figure + 中文图注（用 `*斜体*`）

## 强化学习论文的额外处理（条件性）

写笔记前，先判断本文是否为**强化学习（RL）论文**。

**判断信号（出现任一、且作为方法核心范式使用，即视为 RL 论文）**：
`reinforcement learning` / `policy`（策略）/ `agent`（智能体）/ `environment`（环境）/ `reward` / `reward function` / `MDP` / `state-action` / `episode` / `RLHF` / 算法名 `PPO` `DQN` `SAC` `A3C` `TRPO` `DDPG` `actor-critic` `Q-learning` / `value function` `advantage` `Bellman` / `imitation learning` / `inverse RL`。

> **判断口诀：论文是不是在「训练一个 agent 通过环境反馈的 reward 去优化 policy」？是 → RL，追加 Reward Function 章节。**
> 注意区分：仅在论文里"作为 baseline 提一句 RL"不算；RL 必须是本文方法的核心范式。也要区分**监督学习的 loss** 与 **RL 的 reward**——纯监督学习论文只有第 12 章「损失函数」，无需本节。

**若是 RL 论文，必须做两件事**：

1. 在第 12 章「损失函数」之后追加一节 **「十二·补、奖励函数 Reward Function」**（模板见 `templates/notes_template.md`），覆盖：
   - **MDP 建模**：论文如何把任务形式化为 $(S, A, P, R, \pi)$——状态、动作、转移、奖励、策略各对应论文里的什么；
   - **奖励函数公式** $r(s,a)$ 的具体形式 + 每个 reward 分量的直观解释；
   - **Reward 设计技巧**：是否 reward shaping、稀疏→稠密化、curriculum、负奖励/惩罚项；
   - **Reward 与 Loss 的关系**：reward 如何转化为 policy 的优化目标（return $G_t$ / advantage $A_t$），衔接到第 12 章损失函数。
2. 第 12 章「损失函数」聚焦 **policy/value network 的训练损失**（如 PPO 的 clipped surrogate objective、value loss、entropy bonus），不要把环境 reward 塞进第 12 章——reward 归 Reward Function 章节，loss 归第 12 章。

**非 RL 论文**：跳过本节，并删除模板中 Reward Function 占位章节，不要硬编。

## Figure 提取（自动）

`scripts/extract_figs.py` 实现**无需手动 bbox** 的自动提取，基于三条线索：

1. **caption 锚定**：扫描所有页，按行首正则 `^(Fig(?:ure|\.)?)\s*(\d+)\b` 定位每个 figure 的 caption（不依赖字体加粗，因为 caption 常被切成多 span）。
2. **图页识别**：drawings 计数 ≥ 阈值（默认 100）的页面即为矢量图页。这把光栅图（pdfimages 有效）和矢量图（pdfimages 失效，必须渲染）区分开。
3. **图与 caption 配对**：
   - caption 在图页（同页布局）→ caption_top_y 作为图的下边界
   - caption 在文本页顶部（y<100）→ 图在上一图页
   - caption 在文本页底部（y>500）→ 图在下一图页
   - 图页无 caption → 整页作为 figure（drawings extent 作边界）

**用法：**

```bash
python3 scripts/extract_figs.py <pdf_path> <output_dir> [--dpi 200] [--min-drawings 100]
```

输出 `Figure{N}.png`。如需带语义后缀（推荐），重命名为 `Figure{N}_{english_slug}.png`：

```bash
cd <output_dir>
mv Figure1.png Figure1_concept_bottleneck_model.png
mv Figure2.png Figure2_cohort_evaluation.png
# ...
```

**验证步骤（必做）：**
- 用 Read 工具逐张查看提取出的 PNG，确认：
  - 所有 panel 完整未被裁切
  - 不含页眉/页脚/期刊标识
  - 不含 caption 文本块
  - 不含正文段落
- 若某张图裁切不准，调 `--min-drawings` 阈值或回退到 `pdftoppm` + 手动 bbox。

**适用范围：** Nature / Science / Cell / NEJM 等矢量图论文。对纯光栅图嵌入的 PDF（罕见），改用 `page.get_images()` + `doc.extract_image(xref)`。

## HTML 生成

使用 pandoc + MathJax + 自定义 CSS：

```bash
pandoc "<note>.md" \
  -f markdown -t html5 -s \
  --mathjax \
  --metadata title="<title>" \
  --toc --toc-depth=3 \
  -c "style.css" \
  -o "<note>.html"
```

`style.css` 由 `templates/style.css` 复制到目标目录（首次生成时）。包含响应式布局、表格美化、图片阴影、引用块样式、移动端适配。

## 常见错误

| 错误 | 后果 | 解决 |
|---|---|---|
| **把模板套在纯湿实验论文上** | "损失函数""训练超参数""多模态融合"章节凭空硬编，笔记失真、误导读者 | 触发前先判断论文类型；若论文无 model/training/loss/architecture 概念，改用湿实验笔记结构（背景→假设→实验设计→关键发现→机制→意义→局限），不要硬套本模板 |
| 用 `pdftoppm` 整页截图当 figure | 图中包含正文、页眉、不相关内容 | 用 `extract_figs.py`，按 caption + drawings extent 自动裁剪 |
| 用 `pdfimages` 直接提取嵌入图 | figure 被拆成几十张碎片（子图、图标、文字） | 用 PyMuPDF 渲染整页 + 按坐标裁剪（`extract_figs.py` 默认行为） |
| `--min-drawings` 阈值不当 | 图页识别错误（漏掉简洁图 / 误判文字密集页） | 看脚本输出的 "Figure pages" 列表，按需调阈值 |
| HTML 不加 `--mathjax` | LaTeX 公式（损失函数、attention 等）渲染为原始 TeX | 必须加 `--mathjax` |
| 笔记缺少 12 章节中任一节 | 用户认为笔记不完整 | 严格按模板章节（仅在论文确实无对应内容时可省略并说明，例如纯推理模型无"训练损失"） |
| md 中图片路径用绝对路径 | 移动文件夹后失效 | 用相对路径 `figures/FigureN_xxx.png` |
| 子文件夹放在错误的父目录 | 笔记和 PDF 分开，不方便查看 | 笔记文件夹必须和原始 PDF 文件在同一目录，并用 `mv` 把原 PDF 移进去（非 cp，原位置不再保留） |
| **RL 论文漏写 reward function** | 强化学习论文只写第 12 章「损失函数」（policy/value loss）却不解释环境奖励信号，读者无法理解优化目标从何而来 | 写笔记前先判断是否 RL 论文；若是，必须追加 Reward Function 章节（MDP 建模 + r(s,a) 公式 + reward shaping） |

## Tool Dependencies

执行前确保已安装：
- `pdftotext` / `pdfinfo` / `pdfimages` / `pdftoppm`（poppler-utils）
- `pandoc`（HTML 生成）
- Python 3 + `pymupdf` + `Pillow`（figure 提取）

安装命令（macOS）：
```bash
brew install poppler pandoc
pip3 install --break-system-packages pymupdf pillow
```

## 一句话原则

> **针对 AI4Science / 算法工具类论文（有 model、有 training、有 loss、有 benchmark 的那种），在 PDF 所在目录创建同名文件夹，用 `mv` 把原 PDF 移入 + 12 章节 Chinese 学术笔记 + 原文 figure + MathJax HTML。若判断为强化学习论文，额外追加 Reward Function 章节。湿实验/观察性论文请改用其他笔记结构，不要硬套本模板。**
