# 移动端与响应式底线

这是**硬地板，不是愿望清单**。任何产物都必须在 **320 / 375 / 414 / 768 px** 四个宽度下渲染无瑕。默认按移动优先写 CSS，再用 `min-width` 媒体查询向上扩展。

---

## 一、不可协商项

| # | 规则 | 允许 | 禁止 |
|---|------|------|------|
| 34 | 横向溢出 | `html, body { overflow-x: clip; }` | `overflow-x: hidden`（会破坏 `position: sticky`，还会掩盖真实溢出） |
| 49 | 可点文本 | 按钮、主导航项、页脚链接、面包屑、CTA 在四个宽度都保持单行 | 折成两行的可点文本 |
| 50 | 含图网格轨道 | `grid-template-columns: repeat(auto-fit, minmax(0, 1fr))` | 裸 `1fr`（图片最小内容宽度会撑破轨道） |
| 51 | 超长词 | 展示标题 `overflow-wrap: anywhere; min-width: 0` | 长词溢出容器 |
| 52 | 区块头 | 移动端塌成单列（所有主题变体一致） | 移动端仍强制两列 / 多列 |
| 53 | radio-tab | 切换不滚动跳变 | 切 tab 时页面跳动 |
| 54 | 小节标签 | 标签在标题**上方**、同列垂直堆叠 | 标签在左、标题在右的悬挂式两栏 |

补充：

- 移动端点击目标 ≥ 44px。
- 正文最小可读字号 ≥ 16px（避免 iOS 自动放大输入框）。
- 表格在窄屏要么横向滚动容器（容器自身 `overflow-x: auto`，不污染 `body`），要么改成卡片式堆叠——不许靠 `body` 溢出硬撑。
- 不写脆弱的硬编码视口假设（如 `width: 100vw` 配合 `padding` 会引发横向滚动；改用 `100%` 或 `dvw` 加 `box-sizing`）。
- 字体缩放：避免固定 `px` 高度包裹文本；用 `min-height` 与流式尺寸（`clamp()`）容纳放大。

---

## 二、安全写法片段

```css
/* 根溢出：门 34 */
html, body { overflow-x: clip; }

/* 含图网格：门 50 */
.grid { display: grid; gap: var(--space-md);
        grid-template-columns: repeat(auto-fit, minmax(0, 1fr)); }

/* 展示标题的超长词：门 51 */
.display { font-style: normal; overflow-wrap: anywhere; min-width: 0; }

/* 移动端单列的区块头：门 52 */
.section-head { display: grid; gap: var(--space-sm); grid-template-columns: 1fr; }
@media (min-width: 768px) {
  .section-head { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
}

/* 卡片内长文本不撑破 */
.card { min-width: 0; }
.card p { overflow-wrap: anywhere; }
```

```html
<!-- 表格窄屏：只让容器滚，不让页面滚 -->
<div style="overflow-x: auto;"><table>…</table></div>
```

---

## 三、四个宽度的检查点

| 宽度 | 关注点 |
|------|--------|
| **320** | 最窄现实宽度：可点文本是否折行、标题是否溢出、是否有任何横向滚动 |
| **375** | 主流手机：单列节奏是否成立、间距是否塌缩成 0、底部固定元素是否遮挡内容 |
| **414** | 大屏手机：图片轨道是否被拉变形、两列是否过早出现而显得拥挤 |
| **768** | 平板 / 断点边界：从单列到多列的过渡是否有中间态塌陷、导航是否在此时切换形态 |

四个宽度都要查：**无横向滚动**、无重叠文字、无被裁切内容、无点击目标 <44px、无图片变形。

---

## 四、视觉验证

- 用 `browser_open` 打开产物，用 `browser_screenshot` 抓主视口；需要时缩到 320 / 375 / 414 / 768 分别抓图确认。
- 用 `browser_execute` 或浏览器控制台确认 `document.documentElement.scrollWidth <= window.innerWidth`（无横向溢出）。
- 纯源码检查会漏掉字体导入静默失败、flex 容器塌缩这类问题——**必须真打开看**。

## 五、命令行自查

```bash
# 门 34：不该出现 overflow-x: hidden
grep -rn "overflow-x:\s*hidden" --include=*.html --include=*.css .

# 门 50：含图片的轨道不该裸用 1fr
grep -rn "grid-template-columns" --include=*.css --include=*.html . | grep "1fr" | grep -v "minmax"

# 门 38a / 51：标题里的斜体
grep -rn "<em>\|<i>" --include=*.html . | grep -i "<h[1-6]"

# 点击目标：找可疑的小尺寸
grep -rnE "(height|min-height):\s*(1[0-9]|2[0-9]|3[0-9])px" --include=*.css .
```

命中需人工看上下文，但这些命令能把检查范围收窄到几十行以内。报告里要写清**已验证哪些宽度、用什么方式验证**；无法验证的部分直接说明原因，不要声称验证过。
