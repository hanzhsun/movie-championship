# 数据更新流程

## 1. "从豆瓣更新" 

**触发位置**: 周度记录页面（`activeTab === 'calendar'`）

- 从 `data/watched.xlsx` 提取已有电影的ID集合，用于去重
- 访问豆瓣用户已看电影列表页面
- 跳过已爬取电影（通过ID对比）
- 提取信息：中文标题、上映年份、标记日期、评分、海报URL、电影详情页URL
- 下载海报到`data/posters/`
- 保存新电影信息到 `data/watched.xlsx`

---

## 2. "从IMDb更新" 按钮

**触发位置**: 年度总览页面（`activeTab === 'overview'`）

- 从 `data/watched.xlsx` 读取电影列表
- 访问豆瓣电影详情页（如 `https://movie.douban.com/subject/10430817/`）
- 从 `<div id="info">` 中提取：
   - **genres**: 类型，如 "奇幻"
   - **language**: 语言，如 "德语"
   - **imdb_id**: 如 `tt1745686`
- 跳过已有完整信息的电影
- 使用提取到的 `imdb_id` 访问IMDb页面
- 提取 **imdb_tags**，如 "Action, Drama"
- 更新 `genres`、`language`、`imdb_id`、`imdb_tags` 列
- 保存回 `data/tags.xlsx`
- 翻译 `imdb_tags` 为中文并拆分（如 "Action Epic" → "动作" + "史诗"）
- 合并 `genres` 和 `imdb_tags`为`tags`
- 保存到 `data/tags.xlsx`
- 自动调用 `fetchLocalMovies()` 重新加载数据
- 年度总览页面显示更新后的标签信息