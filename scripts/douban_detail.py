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

imdb_id, genres, language, runtime, year = get_douban_movie_detail(
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
    """Fetch details from Douban detail page.

    Returns (imdb_id, genres, language, runtime, year)
    """
    if not movie_url:
        return None, None, None, None, None

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
        }

        response = requests.get(movie_url, headers=headers, cookies=cookies, timeout=10)
        if response.status_code != 200:
            return None, None, None, None, None
        response.encoding = 'utf-8'

        soup = BeautifulSoup(response.text, 'html.parser')
        info_div = soup.find('div', id='info')

        imdb_id = None
        genres = []
        language = None
        runtime = None
        year = None

        if info_div:
            imdb_link = info_div.select_one('a[href*="imdb.com/title"]')
            if imdb_link:
                imdb_text = imdb_link.get_text(strip=True) or imdb_link.get('href', '')
                match = re.search(r'(tt\d+)', imdb_text)
                if match:
                    imdb_id = match.group(1)
            if not imdb_id:
                imdb_text = info_div.get_text(' ', strip=True)
                match = re.search(r'(tt\d+)', imdb_text)
                if match:
                    imdb_id = match.group(1)

            genre_spans = info_div.select('span[property="v:genre"]')
            genres = [span.get_text(strip=True) for span in genre_spans if span.get_text(strip=True)]
            genres = [g for g in genres if g != '剧情']

            def extract_label_value(label):
                def normalize_label(text):
                    return text.replace(':', '').replace('：', '').strip()

                for span in info_div.select('span.pl'):
                    span_text = normalize_label(span.get_text(strip=True))
                    if span_text == label:
                        current = span.next_sibling
                        parts = []
                        while current:
                            if getattr(current, 'name', None) == 'br':
                                break
                            if isinstance(current, str):
                                if current.strip():
                                    parts.append(current.strip())
                            else:
                                if current.name in ('a', 'span'):
                                    text = current.get_text(strip=True)
                                    if text:
                                        parts.append(text)
                            current = current.next_sibling
                        return ' '.join(parts).strip() if parts else None
                return None

            lang_text = extract_label_value('语言')
            if lang_text:
                language = re.split(r'[/、,，]', lang_text, 1)[0].strip()

            runtime_span = info_div.select_one('span[property="v:runtime"]')
            if runtime_span:
                runtime_text = runtime_span.get('content') or runtime_span.get_text(strip=True)
                match = re.search(r'(\d+)', runtime_text or '')
                if match:
                    runtime = int(match.group(1))

            if runtime is None:
                runtime_text = extract_label_value('片长')
                match = re.search(r'(\d+)', runtime_text or '')
                if match:
                    runtime = int(match.group(1))

            if not genres:
                genre_text = extract_label_value('类型')
                if genre_text:
                    genres = [g.strip() for g in re.split(r'[/、,，]', genre_text) if g.strip() and g != '剧情']

        year_elem = soup.select_one('span.year')
        if year_elem:
            match = re.search(r'(\d{4})', year_elem.get_text(strip=True))
            if match:
                year = int(match.group(1))

        return imdb_id, genres, language, runtime, year

    except Exception:
        return None, None, None, None, None
