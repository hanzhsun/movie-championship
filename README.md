# 🎬 Movie Championship

### 前置要求
- Python 3.8+
- Node.js 14+
- 豆瓣账号 (获取你看过的电影列表)

1. **安装依赖**
```bash
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

2. **配置豆瓣**
复制并编辑配置文件：
```bash
cp douban_config.json.example douban_config.json
```
填入你的豆瓣ID和Cookie

3. **启动应用**
```bash
# 终端1: 启动后端
python app.py

# 终端2: 启动前端
cd frontend && npm start
```

打开 http://localhost:3000 🎉