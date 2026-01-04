# -*- coding: utf-8 -*-
"""
豆瓣电影爬虫模块

**处理函数：**
- `get_douban_movies(user_id, existing_ids=None, force_full=False)`: 从豆瓣爬取用户看过的电影列表

**特点：**
- 支持增量更新（只爬取新电影）
- 支持完整扫描（重新爬取所有电影）
- 自动处理分页
- 提取详细的电影信息

**使用示例：**
```python
from douban_crawler import get_douban_movies

movies, new_count = get_douban_movies(user_id='123456', existing_ids={'123', '456'})
```
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import pandas as pd
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
POSTERS_DIR = os.path.join(DATA_DIR, 'posters')
os.makedirs(POSTERS_DIR, exist_ok=True)

# 豆瓣请求头配置
DOUBAN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate',
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

class DoubanCrawlError(Exception):
    def __init__(self, message, debug=None):
        super().__init__(message)
        self.debug = debug or {}


def poster_ext_from_content_type(content_type):
    if not content_type:
        return None
    content_type = content_type.split(';', 1)[0].strip().lower()
    if content_type == 'image/jpeg':
        return '.jpg'
    if content_type == 'image/png':
        return '.png'
    if content_type == 'image/webp':
        return '.webp'
    return None


def poster_ext_from_url(url):
    if not url:
        return '.jpg'
    path = url.split('?', 1)[0]
    _, ext = os.path.splitext(path)
    ext = ext.lower()
    if ext in ('.jpg', '.jpeg', '.png', '.webp'):
        return '.jpg' if ext == '.jpeg' else ext
    return '.jpg'


def download_poster(poster_url, movie_id, cookies=None, posters_dir=None, debug=False):
    if not poster_url or not movie_id:
        return None
    posters_dir = posters_dir or POSTERS_DIR
    os.makedirs(posters_dir, exist_ok=True)
    for ext in ('.jpg', '.jpeg', '.png', '.webp'):
        existing_path = os.path.join(posters_dir, f"{movie_id}{ext}")
        if os.path.exists(existing_path):
            return existing_path

    candidate_urls = [poster_url]
    if poster_url.endswith('.webp'):
        candidate_urls = [poster_url[:-5] + '.jpg', poster_url]

    headers = DOUBAN_HEADERS.copy()
    headers['Accept'] = 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8'
    headers['Referer'] = 'https://movie.douban.com/'

    for url in candidate_urls:
        try:
            response = requests.get(url, headers=headers, cookies=cookies or {}, timeout=10)
            if response.status_code != 200 or not response.content:
                continue
            ext = poster_ext_from_content_type(response.headers.get('Content-Type', ''))
            if not ext:
                ext = poster_ext_from_url(url)
            file_path = os.path.join(posters_dir, f"{movie_id}{ext}")
            with open(file_path, 'wb') as f:
                f.write(response.content)
            return file_path
        except requests.RequestException:
            if debug:
                continue
            continue
    return None



def get_douban_movies(user_id, existing_ids=None, force_full=False, cookies=None, debug=False, download_posters=True, posters_dir=None, progress_cb=None):
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
    total_count = None
    processed_count = 0
    max_retries = 3
    
    while True:
        url = f'https://movie.douban.com/people/{user_id}/collect?start={start}&sort=time&mode=grid&type=movie'
        
        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=DOUBAN_HEADERS, cookies=cookies or {}, timeout=10)
                status_code = response.status_code
                response_url = response.url
                if status_code != 200:
                    if debug:
                        raise DoubanCrawlError("Douban request failed", debug={"status": status_code, "url": response_url})
                    raise ValueError(f"Douban request failed: status={status_code}, url={response_url}")
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
        if total_count is None:
            count_elem = soup.select_one('span.subject-num')
            if count_elem:
                count_text = count_elem.get_text(' ', strip=True)
                match = re.search(r'/\s*(\d+)', count_text)
                if match:
                    total_count = int(match.group(1))

        
        # 查找所有电影项
        items = soup.find_all('div', class_='item')
        if not items:
            if start == 0:
                url_lower = (response_url or '').lower()
                login_hint = ''
                if 'login' in url_lower or 'passport' in url_lower or 'accounts' in url_lower:
                    login_hint = ' (likely login required)'
                title = soup.title.string.strip() if soup.title and soup.title.string else None
                html_lower = html.lower()
                captcha_hint = False
                if 'captcha' in html_lower or 'verify' in html_lower or 'security check' in html_lower:
                    captcha_hint = True
                debug_info = {
                    'status': status_code,
                    'url': response_url,
                    'title': title,
                    'html_len': len(html),
                    'login_hint': bool(login_hint),
                    'captcha_hint': captcha_hint,
                }
                if debug:
                    raise DoubanCrawlError("No items found on first page", debug=debug_info)
                raise ValueError(f"No items found on first page{login_hint}. url={response_url}, html_len={len(html)}")
            break
        
        page_found_new = False
        movie_id_count = 0
        for item in items:
            try:
                processed_count += 1
                if progress_cb:
                    try:
                        progress_cb(processed_count, total_count, new_count)
                    except Exception:
                        pass
                # 提取电影ID和信息
                movie_id = item.get('data-subject')
                if not movie_id:
                    subject_node = item.select_one('[data-subject]')
                    if subject_node:
                        movie_id = subject_node.get('data-subject')
                if not movie_id:
                    link_candidate = item.find('a', href=re.compile(r'/subject/(\d+)/'))
                    if link_candidate:
                        match = re.search(r'/subject/(\d+)/', link_candidate.get('href', ''))
                        if match:
                            movie_id = match.group(1)
                if movie_id:
                    movie_id_count += 1
                if not movie_id:
                    continue
                
                # 跳过已存在的电影（除非强制全扫描）
                if not force_full and movie_id in existing_ids:
                    continue
                
                page_found_new = True
                
                # 提取电影数据
                # Parse title/link/date/rating/poster from current layout
                title_elem = item.select_one('li.title a') or item.find('a', class_='title') or item.find('a', href=re.compile(r'/subject/\d+/'))
                title = ''
                link = ''
                if title_elem:
                    link = title_elem.get('href', '')
                    em = title_elem.find('em')
                    if em:
                        em_text = em.get_text(strip=True)
                        if em_text:
                            primary = em_text.split('/')[0].strip()
                            title = primary if primary else em_text
                    else:
                        title = title_elem.get_text(' ', strip=True)

                intro_elem = item.select_one('li.intro')
                info_text = intro_elem.get_text(' ', strip=True) if intro_elem else ''

                date_str = ''
                date_elem = item.select_one('span.date')
                if date_elem:
                    date_str = date_elem.get_text(strip=True)
                if not date_str:
                    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', info_text)
                    date_str = date_match.group(1) if date_match else ''

                rating = 0.0
                rating_elem = item.find('span', class_='rating_nums')
                if rating_elem:
                    try:
                        rating = float(rating_elem.text)
                    except ValueError:
                        rating = 0.0
                else:
                    rating_class_elem = item.find('span', class_=re.compile(r'rating\d+-t'))
                    if rating_class_elem:
                        for cls in rating_class_elem.get('class', []):
                            m = re.match(r'rating(\d+)-t', cls)
                            if m:
                                rating = float(m.group(1))
                                break

                img_elem = item.select_one('div.pic img') or item.find('img')
                poster_url = ''
                if img_elem:
                    poster_url = img_elem.get('src') or img_elem.get('data-src') or ''

                if download_posters and poster_url:
                    try:
                        download_poster(poster_url, movie_id, cookies=cookies, posters_dir=posters_dir, debug=debug)
                    except Exception as e:
                        if debug:
                            print(f"Poster download failed for {movie_id}: {e}")
                
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
        
        # If we still have no parsed movies on the first page, surface debug info.
        if start == 0 and debug and not movies:
            title = soup.title.string.strip() if soup.title and soup.title.string else None
            html_lower = html.lower()
            captcha_hint = False
            if 'captcha' in html_lower or 'verify' in html_lower or 'security check' in html_lower:
                captcha_hint = True
            url_lower = (response_url or '').lower()
            login_hint = 'login' in url_lower or 'passport' in url_lower or 'accounts' in url_lower
            debug_info = {
                'status': status_code,
                'url': response_url,
                'title': title,
                'html_len': len(html),
                'item_count': len(items),
                'movie_id_count': movie_id_count,
                'existing_ids_count': len(existing_ids),
                'login_hint': login_hint,
                'captcha_hint': captcha_hint,
                'first_item_snippet': str(items[0])[:500] if items else None,
            }
            raise DoubanCrawlError("No movies parsed from first page", debug=debug_info)

        if not page_found_new and not force_full:
            break
        start += 15
        time.sleep(1)  # 避免被反爬虫限制
    
    return movies, new_count
