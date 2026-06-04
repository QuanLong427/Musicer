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

当收到 "请将以下B站视频转为音频" 的指令时，执行以下步骤：

### 1. 执行转换

调用 `convert_video` 工具，传入 URL 列表：
```
convert_video(urls=["https://www.bilibili.com/video/BV1xxxxx", "https://www.bilibili.com/video/BV2yyyyy"])
```

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
