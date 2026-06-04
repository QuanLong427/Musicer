---
name: cloud-search
description: 通过 B站 API 搜索云端视频资源，支持音乐、科普、课程、演讲、访谈、纪录片等多种类型，只有在本地没有搜索到音乐或者视频资源的时候才使用这个skill
---
## 云端搜索 Skill

通过 B站 搜索资源。B站 拥有各类视频资源（音乐、科普、课程、演讲、访谈、纪录片等），本应用会将视频转为音频供用户收听。

### 使用前提（重要）

**仅在以下情况使用本 Skill：**
1. `local_search` 返回 total=0（本地没有该资源）
2. 用户明确说"去B站搜"、"云端搜索"、"网上找"

**禁止在未调用 local_search 的情况下直接使用本 Skill。**

### 搜索步骤

1. 解析用户意图，提取搜索关键词
2. 使用 `bili_search` 工具搜索B站视频（直接传入中文关键词即可）：
   bili_search(keyword="关键词")
   返回 JSON: { "total": number, "videos": [{ "bvid", "title", "author", "duration", "play", "pic" }] }
3. 分析搜索结果，筛选最相关的视频（通常 5-10 个），以 tracks 格式输出

### 输出格式

搜索结果以 ```tracks 代码块输出，每个对象包含 bvid、title、author、duration、url 字段：

```tracks
[
  {"bvid":"BV1xxxxx","title":"视频标题","author":"UP主","duration":"4:32","url":"https://www.bilibili.com/video/BV1xxxxx"},
  {"bvid":"BV2yyyyy","title":"视频标题2","author":"UP主2","duration":"12:05","url":"https://www.bilibili.com/video/BV2yyyyy"}
]
```

### 搜索后的下一步

搜索到结果后，**提示用户是否需要转换下载**。只有用户确认后，才调用 `convert_video` 工具将视频转为音频并添加到本地曲库。
