# -*- coding: utf-8 -*-
"""
豆瓣电影详情页信息提取脚本

**处理函数：**
- `get_douban_movie_detail(movie_url, cookies=None)`: 从豆瓣电影详情页提取：
  - IMDb ID (imdb_id)
  - 电影类型列表 (genres)
  - 语言 (language)
  - 片长 (runtime) - 单位：分钟

**注意：**
此脚本中的函数在 app.py 中也有实现，用于处理流式 API 请求。
该脚本主要用于独立调试和测试豆瓣数据提取功能。

**使用示例：**
```python
from douban_detail import get_douban_movie_detail

imdb_id, genres, language, runtime = get_douban_movie_detail(
    "https://movie.douban.com/subject/1291546/",
    cookies=your_cookies
)
```
"""
import sys
import os

# 注意：不在这里包装 sys.stdout，因为 app.py 已经处理了编码问题
# 在 Flask 开发模式下，导入时 sys.stdout 可能已关闭，会导致 ValueError

import requests
from bs4 import BeautifulSoup
import re

def get_douban_movie_detail(movie_url, cookies=None):
    """从豆瓣电影详情页提取信息
    
    参数:
        movie_url: 豆瓣电影详情页URL
        cookies: 可选的Cookie字典，用于需要登录的页面
    
    返回: (imdb_id, genres, language, runtime) 元组
    runtime: 片长（分钟），整数
    """
    if not movie_url:
        return None, None, None, None
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
        }
        
        response = requests.get(movie_url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code != 200:
            return None, None, None, None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找 info div
        info_div = soup.find('div', id='info')
        if not info_div:
            return None, None, None, None
        
        imdb_id = None
        genres = []
        language = None
        runtime = None
        
        # 提取 IMDb ID
        for span in info_div.find_all('span', class_='pl'):
            span_text = span.get_text(strip=True)
            if span_text == 'IMDb:' or span_text == 'IMDb':
                # 获取span后面的文本节点
                next_sibling = span.next_sibling
                if next_sibling:
                    imdb_text = next_sibling.strip() if isinstance(next_sibling, str) else next_sibling.get_text(strip=True)
                    if imdb_text:
                        # 从文本中提取 IMDb ID（格式是 "tt6924650"），保留完整的 tt 前缀
                        imdb_match = re.search(r'(tt\d+)', imdb_text)
                        if imdb_match:
                            imdb_id = imdb_match.group(1)
                break
        
        # 提取类型（忽略'剧情'）
        genre_spans = info_div.find_all('span', attrs={'property': 'v:genre'})
        for span in genre_spans:
            genre_text = span.get_text(strip=True)
            if genre_text and genre_text != '剧情':  # 忽略'剧情'
                genres.append(genre_text)
        
        # 提取语言
        for span in info_div.find_all('span', class_='pl'):
            span_text = span.get_text(strip=True)
            if span_text == '语言:' or span_text == '语言':
                # 获取span后面的文本节点（第一个语言）
                current = span.next_sibling
                while current:
                    if hasattr(current, 'name'):
                        if current.name == 'a':
                            language = current.get_text(strip=True)
                            break
                        elif current.name == 'br':
                            break
                    elif isinstance(current, str) and current.strip():
                        # 尝试从文本中提取
                        text = current.strip()
                        if text and text not in ['/', '、']:
                            language = text.split('/')[0].split('、')[0].strip()
                            break
                    current = current.next_sibling
                break
        
        # 提取片长（分钟）
        for span in info_div.find_all('span', class_='pl'):
            span_text = span.get_text(strip=True)
            if span_text == '片长:' or span_text == '片长':
                # 获取span后面的文本节点
                next_sibling = span.next_sibling
                if next_sibling:
                    runtime_text = next_sibling.strip() if isinstance(next_sibling, str) else next_sibling.get_text(strip=True)
                    if runtime_text:
                        # 从文本中提取数字
                        runtime_match = re.search(r'(\d+)\s*分钟', runtime_text)
                        if runtime_match:
                            runtime = int(runtime_match.group(1))
                break
        
        genres_str = ', '.join(genres) if genres else None
        
        return imdb_id, genres_str, language, runtime
        
    except Exception as e:
        # 静默处理错误，返回 None 值
        # 不在这里打印，因为 stdout 可能已关闭（Flask 开发模式）
        # 错误会被上层的 safe_print 处理
        return None, None, None, None
