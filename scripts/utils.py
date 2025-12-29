# -*- coding: utf-8 -*-
"""
公共工具函数库

**处理函数：**
- `get_imdb_tags(imdb_id)`: 从IMDb页面获取标签/类型
  - 输入：IMDb ID (如 'tt1234567')
  - 输出：逗号分隔的标签字符串 (如 'Action, Thriller')
  - 说明：自动忽略语言标签和 'Drama'

**注意：**
此脚本中的函数在 app.py 中也有实现，用于处理流式 API 请求。
该脚本主要用于独立调试和测试 IMDb 数据提取功能。

**使用示例：**
```python
from utils import get_imdb_tags

tags = get_imdb_tags('tt0468569')  # Batman Begins
print(tags)  # 'Action, Crime, Drama, ...'
```

**性能注意：**
- 每个请求有 10 秒超时
- 建议在循环中添加延迟避免反爬虫限制
"""
import sys
import os

# 注意：不在这里包装 sys.stdout，因为 app.py 已经处理了编码问题
# 在 Flask 开发模式下，导入时 sys.stdout 可能已关闭，会导致 ValueError

import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

# 数据目录路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

def get_imdb_tags(imdb_id):
    """从IMDb页面获取标签/类型"""
    if not imdb_id or pd.isna(imdb_id):
        return None
    
    # 确保IMDb ID格式正确
    imdb_id_str = str(imdb_id).strip()
    if not imdb_id_str.startswith('tt'):
        imdb_id_str = f'tt{imdb_id_str}'
    
    url = f'https://www.imdb.com/title/{imdb_id_str}/'
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        tags = []
        
        # 只从 data-testid="interests" 的container中提取标签
        interests_container = soup.find('div', {'data-testid': 'interests'})
        if not interests_container:
            # 如果找不到interests container，尝试查找包含ipc-chip-list的div
            interests_container = soup.find('div', class_=lambda x: x and 'ipc-chip-list' in x and 'ipc-chip-list--baseAlt' in x)
        
        if interests_container:
            # 只从这个container中提取 ipc-chip__text 类的span元素中的标签
            chip_spans = interests_container.find_all('span', class_='ipc-chip__text')
        else:
            # 如果找不到container，回退到原来的方法（但这种情况应该很少）
            chip_spans = soup.find_all('span', class_='ipc-chip__text')
        
        # 语言相关的tag列表（需要忽略）
        language_tags = {
            'English', 'Japanese', 'Chinese', 'French', 'German', 'Spanish', 'Italian', 
            'Korean', 'Russian', 'Portuguese', 'Hindi', 'Arabic', 'Turkish', 'Polish',
            'Dutch', 'Swedish', 'Norwegian', 'Danish', 'Finnish', 'Greek', 'Hebrew',
            'Thai', 'Vietnamese', 'Indonesian', 'Malay', 'Tagalog', 'Mandarin',
            'Cantonese', 'Tamil'
        }
        
        for span in chip_spans:
            chip_text = span.get_text(strip=True)
            # 忽略空字符串、'Drama'和语言相关tag
            if (chip_text and 
                chip_text != 'Drama' and 
                chip_text not in language_tags and
                chip_text not in tags):
                tags.append(chip_text)
        
        # 去重并保持顺序
        tags = list(dict.fromkeys(tags))
        
        if tags:
            return ', '.join(tags)
        else:
            return None
            
    except Exception as e:
        # 静默处理错误，返回 None
        # 不在这里打印，因为 stdout 可能已关闭（Flask 开发模式）
        # 错误会被上层的 safe_print 处理
        return None

