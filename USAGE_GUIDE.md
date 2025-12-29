# 电影评分系统 - 使用指南

## 系统架构

该系统由以下三个主要部分组成：

### 1. 后端 (app.py)
- Flask 服务器，提供 REST API
- 支持从豆瓣和 IMDb 爬取电影数据
- 处理数据的存储和转换

### 2. 前端 (frontend/)
- React + TypeScript 应用
- 两个主要视图：周度记录（calendar）和年度总览（overview）

### 3. 数据存储 (data/)
- `watched.xlsx`: 从豆瓣爬取的原始电影数据
- `tags.xlsx`: 带有标签和详细信息的电影数据
- `posters/`: 电影海报存储目录

## 工作流程

### 第一步：配置豆瓣账号

1. 创建 `douban_config.json` 文件（在项目根目录）：

```json
{
  "user_id": "你的豆瓣用户ID",
  "cookies": {
    "dbcl2": "你的豆瓣 Cookie 中的 dbcl2 值"
  }
}
```

2. 获取豆瓣 Cookie 方法：
   - 登录豆瓣账号
   - 打开浏览器开发者工具（F12）
   - 进入 Network 标签
   - 访问任意豆瓣页面
   - 找到请求中的 Cookie，复制 dbcl2 值

### 第二步：从豆瓣更新电影

1. 启动后端服务：
```bash
python app.py
```

2. 启动前端应用：
```bash
cd frontend && npm start
```

3. 在浏览器中打开 `http://localhost:3000`

4. 点击"周度记录"（calendar）标签页

5. 点击"从豆瓣更新"按钮

6. 等待爬取完成，系统会自动保存到 `data/watched.xlsx`

### 第三步：从 IMDb 更新标签

1. 在"年度总览"（overview）标签页

2. 点击"从IMDb更新"按钮

3. 系统会：
   - 读取 `watched.xlsx` 中的电影
   - 访问豆瓣详情页获取：genres（类型）、language（语言）、imdb_id、runtime（片长）
   - 访问 IMDb 页面获取标签
   - 翻译 IMDb 标签为中文
   - 合并 genres 和翻译后的标签
   - 保存到 `data/tags.xlsx`

4. 更新完成后，前端自动重新加载数据并显示

## API 接口

### 获取电影数据

**GET /api/movies/watched**
- 获取 watched.xlsx 中的电影数据（用于周度记录）

**GET /api/movies/tags**
- 获取 tags.xlsx 中的电影数据（用于年度总览）

### 更新电影数据

**POST /api/movies/update-douban**
- 从豆瓣更新电影列表
- 返回：成功/失败 + 更新数量

**POST /api/movies/update-imdb**
- 从豆瓣和 IMDb 更新电影详情和标签
- 支持流式响应，显示实时进度
- 返回：进度更新和最终结果

## 数据格式

### watched.xlsx 列结构
- `id`: 豆瓣电影 ID
- `title`: 电影标题（中文）
- `date`: 标记日期
- `rating`: 用户评分（1-5 星）
- `poster`: 海报 URL
- `url`: 豆瓣电影详情页 URL

### tags.xlsx 列结构
- 包含 watched.xlsx 的所有列
- `genres`: 豆瓣电影类型（逗号分隔，如 "冒险,科幻"）
- `language`: 电影语言
- `imdb_id`: IMDb ID（如 tt1234567）
- `imdb_tags`: IMDb 标签（逗号分隔，如 "Action, Thriller"）
- `tags`: 合并后的标签（斜杠分隔，如 "冒险/科幻/动作/惊悚"）
- `runtime`: 片长（分钟）

## 标签翻译映射

系统包含以下常见 IMDb 标签的中文翻译：

| IMDb | 中文 |
|------|------|
| Action | 动作 |
| Adventure | 冒险 |
| Animation | 动画 |
| Comedy | 喜剧 |
| Crime | 犯罪 |
| Documentary | 纪录片 |
| Family | 家庭 |
| Fantasy | 奇幻 |
| History | 历史 |
| Horror | 恐怖 |
| Music | 音乐 |
| Mystery | 悬疑 |
| Romance | 爱情 |
| Sci-Fi | 科幻 |
| Thriller | 惊悚 |
| War | 战争 |

### 组合标签翻译

系统还支持组合标签翻译，例如：

- "Action Epic" → "动作" + "史诗"
- "Romantic Comedy" → "爱情" + "喜剧"
- "Psychological Horror" → "心理" + "恐怖"
- "Sci-Fi Epic" → "科幻" + "史诗"

## 常见问题

### 1. 爬取速度太慢？
- 系统在爬取时已添加延迟，避免被豆瓣/IMDb 反爬虫限制
- 这是正常的，请耐心等待

### 2. 某些电影无法获取 IMDb 信息？
- 可能是因为豆瓣详情页中没有 IMDb ID
- 或者 IMDb 页面结构与预期不同
- 系统会自动跳过这些电影

### 3. 标签翻译不准确？
- 可以在 app.py 中的 `IMDB_TAG_TRANSLATION` 字典中调整翻译
- 如果需要添加新的翻译，请修改该字典

### 4. 前端显示的电影数据与文件不一致？
- 可以点击"更新"按钮刷新数据
- 或者直接修改 Excel 文件后重启服务

## 文件结构

```
movie-championship/
├── app.py                    # 后端应用
├── douban_config.json        # 豆瓣配置（不要上传到 Git）
├── requirements.txt          # Python 依赖
├── data/
│   ├── watched.xlsx         # 豆瓣电影数据
│   ├── tags.xlsx            # 带标签的电影数据
│   └── posters/             # 电影海报
├── frontend/                # React 前端应用
│   ├── src/
│   │   ├── App.tsx          # 主应用组件
│   │   ├── App.css
│   │   └── index.tsx
│   ├── package.json
│   └── public/
└── scripts/
    ├── douban_detail.py     # 豆瓣详情页爬虫
    ├── merge_tags.py        # 标签合并脚本
    └── utils.py             # 工具函数
```

## 故障排除

### 后端无法启动？
1. 检查 Python 版本（需要 3.8+）
2. 确保已安装所有依赖：`pip install -r requirements.txt`
3. 检查 `douban_config.json` 文件存在且格式正确

### 前端无法连接到后端？
1. 确保后端已启动（默认端口 5000）
2. 检查 `frontend/src/App.tsx` 中的 `API_BASE_URL` 配置
3. 检查浏览器控制台是否有 CORS 错误

### 无法爬取豆瓣数据？
1. 检查豆瓣 Cookie 是否过期
2. 检查豆瓣 ID 是否正确
3. 查看后端日志获取详细错误信息

## 性能优化建议

1. **减少网络请求**：避免频繁点击更新按钮
2. **增加延迟**：如果被反爬虫限制，可增加 `time.sleep()` 的延迟
3. **分批处理**：对于大量电影，可考虑分批更新
4. **本地缓存**：可添加 IMDb 标签缓存机制

## 开发和贡献

### 添加新的标签翻译

编辑 `app.py` 中的 `IMDB_TAG_TRANSLATION` 字典：

```python
IMDB_TAG_TRANSLATION = {
    # 添加新的翻译
    'NewTag': ['新标签'],
    'Composite Tag': ['组合', '标签'],
}
```

### 修改前端界面

编辑 `frontend/src/App.tsx` 中的相关组件和样式。

### 调试爬虫

运行测试脚本：

```bash
python test_tags.py  # 测试标签翻译
```

## 许可证

该项目采用 MIT 许可证。

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。
