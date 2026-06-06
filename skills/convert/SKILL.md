---
name: convert
description: 将 B站视频转为 MP3 音频文件，支持批量转换和自动重命名
---
## 转换 Skill

**使用前提：**
- 本 Skill 是**云端搜索后的收尾步骤**，不是独立入口
- **严禁**在未搜索云端的情况下直接调用 convert_video
- 仅在 `bili_search` 返回结果且用户确认下载后使用

**关键规则：**
1. **使用 `convert_video` 工具执行转换，不要使用 bash**
2. **不要使用 which、find、ls 或任何命令探索/验证路径**
3. **直接调用工具，无需验证**
4. **工具内部使用 `npx bv2mp3 --threads 20` 执行转换**
5. **必须等待 `convert_video` 工具返回结果后，才能执行后续步骤或输出结束语**
6. **禁止在调用 convert_video 之前或期间输出"转换已启动"、"请稍候"等结束语**
7. **必须传入 `song_meta_json` 参数，格式见下方，artist 和 title 必须从视频标题中解析出纯净的歌手名和歌名**

**Fallback 规则（工具内部自动处理）：**
- `artist` 缺失 → 自动使用 `"Unknown"`
- `title` 缺失 → 自动使用 `videoTitle`（原始视频标题）
- `bvid` → 始终存在（由 bili_search 保证）

当收到 "请将以下B站视频转为音频" 的指令时，执行以下步骤：

### 1. 解析元数据

从 `bili_search` 返回的搜索结果中，为每个视频提取以下字段：

- **`bvid`**：BV 号（必填）
- **`title`**：纯净歌名（必填，从视频标题中提取，去除UP主名、前缀描述、后缀标签等噪音）
- **`artist`**：纯净歌手名（必填，从视频标题中提取，不是 UP 主名字）
- **`uploader`**：UP 主名字（来自 bili_search 的 author 字段）
- **`videoTitle`**：视频原始标题（来自 bili_search 的 title 字段）

**解析规则：**
- 视频标题中 `《》` 内的内容为歌名，如 `新裤子《没有理想的人不伤心》` → 歌名 = `没有理想的人不伤心`
- 歌名前面的部分通常包含歌手名，如 `新裤子《...》` → 歌手 = `新裤子`
- 去掉前缀描述（如"在百万豪装录音棚大声听"、"4K修复"、"【Hi-Res无损】"等）
- 去掉后缀标签（如"【Hi-res】"、"- MV"等）
- UP 主名字（如 "JLRS-LeoFM"）是频道名，不是歌手名

示例：
```
视频标题: "在百万豪装录音棚大声听 新裤子《没有理想的人不伤心》【Hi-res】"
UP主: "JLRS-LeoFM"
→ artist: "新裤子", title: "没有理想的人不伤心"
```

### 2. 执行转换

调用 `convert_video` 工具，传入 URL 列表和解析后的元数据：
```
convert_video(
  urls=["https://www.bilibili.com/video/BV1xxxxx", "https://www.bilibili.com/video/BV2yyyyy"],
  song_meta_json='[{"bvid":"BV1xxxxx","title":"没有理想的人不伤心","artist":"新裤子","uploader":"JLRS-LeoFM","videoTitle":"在百万豪装录音棚大声听 新裤子《没有理想的人不伤心》【Hi-res】"},{"bvid":"BV2yyyyy","title":"歌名2","artist":"歌手2","uploader":"UP2","videoTitle":"原始标题2"}]'
)
```

`song_meta_json` 格式：JSON 数组字符串，每个元素包含 `bvid`（BV号）、`title`（纯净歌名）、`artist`（纯净歌手名）、`uploader`（UP主名字）、`videoTitle`（视频原始标题）。**title 和 artist 必须为空字符串以外的值**。

### 2. 扫描曲库

调用 `bash` 工具执行：
```
TODAY=$(date +%Y%m%d)
curl -s -G "http://localhost:8000/api/tracks/scan" -d "subDir=$TODAY&baseDir=$MUSIC_DIR"
```

返回 JSON: { "tracks": [{ "id", "title", "author", "url", ... }] }

### 3. 为每个 track 补上 bvid

根据 scan 结果和视频 BV 号，在 track 对象中添加 "bvid" 字段。**严禁遗漏 bvid 字段**

### 4. 将新增的 tracks 数据直接用 added 代码块输出

```added
[
  {"id":"20250430/文件名.mp3","title":"标题","author":"作者","url":"/api/tracks/20250430/%E6%96%87%E4%BB%B6%E5%90%8D.mp3","date":"","filename":"文件名.mp3","subDir":"20250430","size":12345,"bvid":"BV1xxxxxx"}
]
```

added 代码块规则：

- 直接复制 scan API 返回的 track 对象，不要自行编造或修改 url 字段
- 每个 track 对象**必须**包含 "bvid" 字段
- 即使只有一个文件也用数组格式
- **严禁**手动拼接 url，必须使用 scan API 返回的 url

### 5. 清理 .flv 文件

此步骤由 `convert_video` 工具自动执行，无需手动操作。工具返回的输出中会包含 `[cleanup] Deleted X .flv file(s)` 信息。
