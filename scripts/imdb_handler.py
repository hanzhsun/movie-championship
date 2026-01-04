# -*- coding: utf-8 -*-
"""
IMDb 标签处理模块 - 轻量级包装，核心翻译逻辑导入自 merge_tags

**处理函数：**
- `get_imdb_tags(imdb_id)`: 从 IMDb 页面获取标签
- `translate_imdb_tag(tag)`: 翻译单个标签（导入自 merge_tags，支持组合标签拆分）
- `merge_movie_tags(genres_list, imdb_tags_list)`: 合并标签

**设计原则：**
- 避免代码重复：翻译逻辑在 merge_tags.py 中维护
- 单一职责：此模块只负责 IMDb 爬虫和标签合并
- 翻译字典完整：translate_imdb_tag 已支持组合标签拆分 (如 'Action Epic' → ['动作', '史诗'])
- 便于测试：可独立导入使用

**使用示例：**
```python
from imdb_handler import get_imdb_tags, merge_movie_tags
from merge_tags import translate_imdb_tag

tags = get_imdb_tags('tt1234567')
translated = translate_imdb_tag('Action Epic')  # 直接得到 ['动作', '史诗']
merged = merge_movie_tags(['动作'], ['科幻'])
```
"""

import requests
from bs4 import BeautifulSoup

def get_imdb_tags(imdb_id):
    """从 IMDb 页面获取标签
    
    参数:
        imdb_id: IMDb ID (例如 'tt1234567')
    
    返回: 逗号分隔的标签字符串 (例如 'Action, Thriller, Crime')
    """
    if not imdb_id:
        return ""
    
    try:
        imdb_id_str = str(imdb_id).strip()
        if not imdb_id_str.startswith('tt'):
            imdb_id_str = f'tt{imdb_id_str}'
        url = f"https://www.imdb.com/title/{imdb_id_str}/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""
        response.encoding = 'utf-8'
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        tags = []

        interests_section = (
            soup.find('section', {'data-testid': 'interests'})
            or soup.find('div', {'data-testid': 'interests'})
        )
        chip_container = None
        if interests_section:
            chip_container = interests_section.find('div', class_='ipc-chip-list__scroller') or interests_section
        if not chip_container:
            chip_container = soup.find('div', class_='ipc-chip-list__scroller')
        if chip_container:
            chip_spans = chip_container.find_all('span', class_='ipc-chip__text')
            for span in chip_spans:
                text = span.get_text(strip=True)
                if text and text not in tags:
                    tags.append(text)
        
        # 过滤掉语言标签和不需要的通用标签
        filtered_tags = []
        languages = ['English', 'Spanish', 'French', 'German', 'Italian', 'Japanese', 
                     'Chinese', 'Korean', 'Russian', 'Hindi']
        
        for tag in tags:
            if tag in languages or tag == 'Drama':
                continue
            filtered_tags.append(tag)
        
        return ', '.join(filtered_tags) if filtered_tags else ""
        
    except Exception as e:
        print(f"获取 IMDb 标签失败: {e}")
        return ""


def merge_movie_tags(genres_list, imdb_tags_list):
    """合并豆瓣 genres 和翻译后的 IMDb 标签
    
    参数:
        genres_list: 豆瓣类型列表 (例如 ['动作', '冒险'])
        imdb_tags_list: 翻译后的 IMDb 标签列表 (例如 ['科幻', '动作'])
    
    返回: 合并后的标签字符串，使用斜杠分隔 (例如 '动作/冒险/科幻')
    """
    if not genres_list and not imdb_tags_list:
        return ""
    
    # 合并列表并去重
    all_tags = []
    seen = set()
    
    # 先加入 genres
    for tag in (genres_list or []):
        if tag and tag not in seen:
            all_tags.append(tag)
            seen.add(tag)
    
    # 再加入 imdb_tags
    for tag in (imdb_tags_list or []):
        if tag and tag not in seen:
            all_tags.append(tag)
            seen.add(tag)
    
    # 使用斜杠连接（前端需要）
    return '/'.join(all_tags) if all_tags else ""
