# Easy Follow Builders — AI Builders 中文日报 Skill

追踪顶尖 AI builders（Karpathy、Swyx、Garry Tan、Sam Altman 等）在 X、播客、官方博客的
动态，自动聚合成一份**中文日报**。

## 这份日报长什么样（每条四段）

1. **中文总结**
2. **中文全文翻译**（原始英文全文的中文译本，不展示英文原文）
3. **推荐理由**（为什么值得看）
4. **原文链接**

## 安装

1. 把整个 `easy-follow-builders/` 文件夹放到：
   `~/.workbuddy/skills/easy-follow-builders/`
   （其他支持该 skill 格式的客户端，放到对应的 skills 目录即可）
2. 默认的「对话内输出」模式**不需要任何安装**。只有在想用 Telegram / 邮箱自动推送时，
   才需要进入 `scripts/` 执行一次 `npm install`（安装 dotenv）。
3. 在对话里说「给我来一份 AI builders 日报」、输入 `/ai`，或直接表达「看看最近 AI 圈发生了什么」「帮我看看最近的新闻」这类意图，即可触发。

## 关于「自动」模型模式

本 skill **完全不依赖某个特定模型**。所有输出格式都由 `SKILL.md` 与 `prompts/` 里的
指令 + 具体样例规定，因此无论你用的是「自动」路由还是手动指定模型，都会得到一致的
中文四段式日报。

## 网络说明

内容来自一个公开的 central feed（见 `config/feeds.json`）。
- 若运行环境能直连 GitHub：脚本自动抓取，全自动出报。
- 若脚本的 Node 出网被挡：agent 会自动改用自身的 WebFetch 通道抓取同样的 feed，
  效果完全一致（skill 内部已处理，你无需任何操作）。

## 自定义

- 改语言 / 频率 / 投递方式：直接跟 agent 说即可。
- 改某类内容的写法：编辑 `prompts/` 下对应文件（或复制到 `~/.follow-builders/prompts/` 覆盖）。
- 源列表由上游统一维护，不能自行增删。

由 Easy Follow Builders skill 生成：https://github.com/zarazhangrui/follow-builders
