# -*- coding: utf-8 -*-
"""
豆瓣电影爬虫模块

**处理函数：**
- `get_douban_movies(user_id, existing_ids=None, force_full=False)`: 从豆瓣爬取用户看过的电影列表
- `get_douban_movie_detail(movie_url, cookies=None)`: 从豆瓣电影详情页提取信息

**特点：**
- 支持增量更新（只爬取新电影）
- 支持完整扫描（重新爬取所有电影）
- 自动处理分页
- 提取详细的电影信息

**使用示例：**
```python
from douban_crawler import get_douban_movies, get_douban_movie_detail

# 爬取豆瓣电影
movies, new_count = get_douban_movies(user_id='123456', existing_ids={'123', '456'})

# 提取单个电影详情
imdb_id, genres, language, runtime = get_douban_movie_detail(movie_url, cookies)
```
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import os

# 豆瓣请求头配置
DOUBAN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'document',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-Site': 'same-origin',
    'Sec-Fetch-User': '?1',
    'Cache-Control': 'max-age=0',
    'Referer': 'https://movie.douban.com/',
    'DNT': '1',
}


def get_douban_movies(user_id, existing_ids=None, force_full=False):
    """从豆瓣爬取用户看过的电影列表
    
    参数:
        user_id: 豆瓣用户ID
        existing_ids: 已存在的电影ID集合（用于增量更新）
        force_full: 是否强制完整扫描
    
    返回: (movies_list, new_count) 元组
        movies_list: 电影字典列表
        new_count: 新增电影数
    """
    if existing_ids is None:
        existing_ids = set()
    
    movies = []
    start = 0
    new_count = 0
    max_retries = 3
    
    while True:
        url = f'https://movie.douban.com/people/{user_id}/collect?start={start}&sort=time&rating=&filter=&mode=grid'
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=DOUBAN_HEADERS, timeout=10)
                response.encoding = 'utf-8'
                html = response.text
                break
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                else:
                    raise e
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 查找所有电影项
        items = soup.find_all('div', class_='item')
        if not items:
            break
        
        page_found_new = False
        for item in items:
            try:
                # 提取电影ID和信息
                movie_id = item.get('data-subject')
                if not movie_id:
                    continue
                
                # 跳过已存在的电影（除非强制全扫描）
                if not force_full and movie_id in existing_ids:
                    continue
                
                page_found_new = True
                
                # 提取电影数据
                title_elem = item.find('a', class_='title')
                title = title_elem.text if title_elem else ''
                
                link_elem = item.find('a', class_='title')
                link = link_elem.get('href') if link_elem else ''
                
                info_elem = item.find('p', class_='info')
                info_text = info_elem.text if info_elem else ''
                
                # 解析日期和评分
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                date_str = date_match.group(1) if date_match else ''
                
                rating_elem = item.find('span', class_='rating_nums')
                rating = float(rating_elem.text) if rating_elem else 0.0
                
                # 提取海报
                img_elem = item.find('img')
                poster_url = img_elem.get('src') if img_elem else ''
                
                movie = {
                    'id': movie_id,
                    'title': title,
                    'link': link,
                    'date': date_str,
                    'rating': rating,
                    'poster_url': poster_url
                }
                
                movies.append(movie)
                new_count += 1
                
            except Exception as e:
                print(f"处理电影项错误: {e}")
                continue
        
        # 如果这一页没有找到新电影（增量更新时），可以停止
        if not page_found_new and not force_full:
            break
        
        start += 15
        time.sleep(1)  # 避免被反爬虫限制
    
    return movies, new_count


def get_douban_movie_detail(movie_url, cookies=None):
    """从豆瓣电影详情页提取信息
    
    参数:
        movie_url: 豆瓣电影详情页URL
        cookies: 可选的Cookie字典，用于需要登录的页面
    
    返回: (imdb_id, genres, language, runtime) 元组
        - imdb_id: IMDb ID (例如 'tt1234567')
        - genres: 类型列表 (例如 ['动作', '冒险'])
        - language: 语言 (例如 '英语')
        - runtime: 片长（分钟），整数
    """
    if not movie_url:
        return None, None, None, None
    
    try:
        headers = DOUBAN_HEADERS.copy()
        response = requests.get(
            movie_url,
            headers=headers,
            cookies=cookies if cookies else {},
            timeout=10
        )
        response.encoding = 'utf-8'
        html = response.text
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 提取IMDb ID
        imdb_id = None
        imdb_link = soup.find('a', href=re.compile(r'imdb\.com/title/'))
        if imdb_link:
            imdb_url = imdb_link.get('href', '')
            match = re.search(r'(tt\d+)', imdb_url)
            if match:
                imdb_id = match.group(1)
        
        # 提取类型
        genres = []
        genre_elem = soup.find('span', string='类型:')
        if genre_elem:
            genre_section = genre_elem.parent
            if genre_section:
                genre_links = genre_section.find_all('a')
                genres = [link.text.strip() for link in genre_links]
        
        # 提取语言
        language = None
        lang_elem = soup.find('span', string='语言:')
        if lang_elem:
            lang_section = lang_elem.parent
            if lang_section:
                lang_link = lang_section.find('a')
                if lang_link:
                    language = lang_link.text.strip()
        
        # 提取片长
        runtime = None
        runtime_elem = soup.find('span', string='片长:')
        if runtime_elem:
            runtime_text = runtime_elem.parent.text
            match = re.search(r'(\d+)\s*分钟', runtime_text)
            if match:
                runtime = int(match.group(1))
        
        return imdb_id, genres, language, runtime
        
    except Exception as e:
        print(f"获取豆瓣电影详情失败: {e}")
        return None, None, None, None
