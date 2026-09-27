# 负向钳制词表与平台语法

本文件展开 [`../SKILL.md`](../SKILL.md) 第四节。核心原则：**负向提示词不是随手加几个词，而是由正向决策反向编译出来的。** 正向决定了什么必须在，负向就决定了什么绝不能在；两者是同一套决策的两面。

---

## 一、反美颜双向钳制

AI 默认倾向于生成"过度平滑、无瑕疵"的图像，导致画面缺乏故事感。此机制用于对抗 AI 的默认审美。

### 1.1 正向反美颜注入（写进正向提示词）

```
visible skin texture, realistic pores, peach fuzz in the light,
subtle skin imperfections, natural skin oiliness,
fabric texture detail, material grain
```

按画面适用性选取，但**至少必须包含** `visible skin texture, realistic pores, peach fuzz in the light` 三项。

### 1.2 负向反美颜高压钳制（写进负向提示词）

```
(overly smooth:1.3), (plastic skin:1.3), (instagram filter:1.2),
(liquefied effect:1.2), (airbrushed:1.2), perfect symmetry,
(waxy skin:1.2), (porcelain skin:1.2), 3d render style, cgi look
```

这些词**无例外全部列入**，不因题材而删减。若用户明确要求"广告级精修"，可把权重降到 1.0，但不得删除。

---

## 二、反向编译规则

负向词由正向决策**反向编译**：

| 正向决策来源 | 反向编译为负向词 | 编译要求 |
|---|---|---|
| 色彩剧本·禁止色清单 | 所有禁止色相全部列入 | 具体到色相名：`saturated yellow, warm orange, pure green, bright red` |
| 光学策略·取景排除项 | 排除的焦段、取景、景深效果全部列入 | 如剔除了天空 → `sky, bright sky`；排除全身 → `full body shot` |
| 叙事脉冲·否定动态 | 被否定的动作与情绪全部列入 | 如"非奔跑" → `running, motion blur of running` |
| 人物谱系·排除物件 | 排除的饰物、服装风格、妆造风格全部列入 | 如"无饰物" → `jewelry, necklace, earrings` |
| 反美颜系统 | 上节 1.2 全部钳制词列入 | 无例外 |

**生成逻辑：** 凡色彩剧本禁止的色相全部列入；凡光学策略排除的焦段/取景全部列入；凡叙事脉冲否定的动态或情绪全部列入；凡反美颜系统钳制的质感全部列入。**无例外，无遗漏。**

---

## 三、通用质量负向词（按需叠加，可跨题材复用）

**结构类**：`extra fingers, fused fingers, extra limbs, deformed hands, bad anatomy, malformed face, asymmetric eyes, watermark, text, signature, logo, jpeg artifacts`

**成像类**：`blurry, out of focus (仅在焦点区域外使用时才安全，见下方警告), low resolution, oversharpened, hdr overprocessing, chromatic aberration (仅当你不想要色散时), motion blur (仅当你不想要动感时)`

**风格类**：`cartoon, anime, illustration, flat lighting, clip art, vector art, painting, digital art look, oversaturated`

> **警告——负向词会与正向词打架：** 模块 4 要求镜头瑕疵（色散、暗角、运动模糊）写入正向。此时**不要**在负向里写 `chromatic aberration` 或 `motion blur`，否则会互相抵消。规则：**凡正向已明确要求的物理特征，一律不得出现在负向词中。**

---

## 四、分题材补充负向词

| 题材 | 补充正向 | 补充负向 |
|---|---|---|
| 赛博朋克 | `neon signage, wet asphalt reflections, volumetric rain` | `clean street, sunny day, cheerful pastel palette` |
| 武侠/古装 | `silk texture, wooden architecture, moonlit bamboo` | `modern clothing, plastic props, contemporary signage` |
| 恐怖 | `dense fog, single practical light, deep crushed blacks` | `bright even lighting, cheerful colors, well-lit room` |
| 纪实/街头 | `available light, candid framing, slight camera shake` | `studio lighting, posed perfection, seamless backdrop` |
| 科幻太空 | `hard vacuum lighting, single-source sun, sharp shadow terminator` | `lens flare spam, colorful nebula, soft ambient fill` |
| 浪漫/回忆 | `soft diffusion, warm practical lamps, gentle halation` | `harsh shadows, clinical white light, high contrast` |

---

## 五、各平台语法差异

| 平台 | 负向词写法 | 备注 |
|---|---|---|
| **Stable Diffusion / ComfyUI** | 独立的 `Negative prompt` 输入框，权重用 `(词:1.2)` | 本文件默认格式，权重语法完全适用 |
| **Midjourney** | 追加在提示词末尾：`--no plastic skin, overly smooth, watermark` | `--no` **不支持权重语法**，去掉 `(词:1.x)` 外壳，只留词本身 |
| **DALL·E / GPT 图像** | 无负向字段，改写为自然语言排除句：`Avoid plastic-looking skin, over-smoothing, and any watermark.` | 把负向清单转写成一句"避免……"的英文指令 |
| **视频模型（Runway / Kling / Sora 等）** | 通常有 negative prompt 字段；无则并入自然语言描述 | 额外补充时间维度的负向：`flickering, morphing face, jittery motion, sudden lighting change` |

切换平台时**词表不变，只换外壳**——反向编译出的语义项一个都不能丢。

---

## 六、负向提示词组装顺序（推荐）

```
[反美颜钳制]  (overly smooth:1.3), (plastic skin:1.3), ...
[禁止色]      saturated yellow, warm orange, pure green, ...
[排除取景]    sky, full body shot, wide angle, ...
[否定动态]    running, smiling, ...
[排除物件]    jewelry, modern clothing, ...
[通用质量]    extra fingers, bad anatomy, watermark, text, ...
```

顺序不影响模型对所有词的计算，但固定顺序便于逐项核对"是否漏编译"。
