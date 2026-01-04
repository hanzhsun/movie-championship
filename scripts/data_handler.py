# -*- coding: utf-8 -*-
"""
数据处理和文件操作模块

**处理函数：**
- `load_douban_config(config_file)`: 加载豆瓣配置
- `convert_dataframe_to_dict_list(df)`: 将 DataFrame 转换为字典列表
- `load_watched_movies(file_path)`: 加载 watched.xlsx
- `load_tags_movies(file_path)`: 加载 tags.xlsx
- `get_tag_movies_mapping(file_path)`: 获取标签与电影的映射
- `stream_response_generator(message)`: 生成流式响应格式

**特点：**
- 支持多种数据格式
- 自动处理文件不存在的情况
- 提供流式响应支持

**使用示例：**
```python
from data_handler import load_douban_config, load_watched_movies, stream_response_generator

# 加载配置
user_id, cookies = load_douban_config('douban_config.json')

# 加载电影数据
movies_df = load_watched_movies('data/watched.xlsx')

# 生成流式响应
response = stream_response_generator('处理中...')
```
"""

import json
import os
import pandas as pd
from io import StringIO


def normalize_cookies(cookies):
    if isinstance(cookies, dict):
        return cookies
    if isinstance(cookies, list):
        result = {}
        for item in cookies:
            if isinstance(item, dict):
                name = item.get('name')
                value = item.get('value')
                if name and value is not None:
                    result[name] = value
        return result
    if isinstance(cookies, str):
        result = {}
        parts = [p.strip() for p in cookies.split(';') if p.strip()]
        for part in parts:
            if '=' in part:
                key, value = part.split('=', 1)
                result[key.strip()] = value.strip()
        return result
    return {}


def load_douban_config(config_file):
    """加载豆瓣配置
    
    参数:
        config_file: 配置文件路径
    
    返回: (user_id, cookies) 元组
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"配置文件不存在: {config_file}\n请创建 douban_config.json 并填入你的豆瓣用户ID和Cookie")
    
    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    user_id = config.get('user_id')
    cookies = normalize_cookies(config.get('cookies', {}))
    if not user_id:
        raise ValueError("配置文件中缺少 user_id")
    
    return user_id, cookies


def convert_dataframe_to_dict_list(df):
    """将 DataFrame 转换为字典列表
    
    参数:
        df: pandas DataFrame
    
    返回: 字典列表，其中 NaN 值被转换为 None
    """
    # 将 DataFrame 转换为字典列表
    records = df.to_dict('records')
    
    # 将 NaN 值转换为 None
    def convert_nan(obj):
        if pd.isna(obj):
            return None
        return obj
    
    return [
        {k: convert_nan(v) for k, v in record.items()}
        for record in records
    ]


def load_watched_movies(file_path):
    """加载 watched.xlsx 文件
    
    参数:
        file_path: watched.xlsx 文件路径
    
    返回: DataFrame，如果文件不存在则返回空 DataFrame
    """
    def csv_fallback_path(xlsx_path):
        base, _ = os.path.splitext(xlsx_path)
        return base + '.csv'

    if not os.path.exists(file_path):
        csv_path = csv_fallback_path(file_path)
        if os.path.exists(csv_path):
            try:
                return pd.read_csv(csv_path)
            except Exception as e:
                print(f"Loading CSV fallback failed: {e}")
        # 返回空 DataFrame，包含预期的列
        return pd.DataFrame(columns=['id', 'title', 'link', 'date', 'rating', 'poster_url'])
    
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"加载 {file_path} 失败: {e}")
        csv_path = csv_fallback_path(file_path)
        if os.path.exists(csv_path):
            try:
                return pd.read_csv(csv_path)
            except Exception as csv_e:
                print(f"Loading CSV fallback failed: {csv_e}")
        return pd.DataFrame(columns=['id', 'title', 'link', 'date', 'rating', 'poster_url'])


def load_tags_movies(file_path):
    """加载 tags.xlsx 文件
    
    参数:
        file_path: tags.xlsx 文件路径
    
    返回: DataFrame，如果文件不存在则返回空 DataFrame
    """
    if not os.path.exists(file_path):
        # 返回空 DataFrame，包含预期的列
        return pd.DataFrame(columns=['id', 'title', 'link', 'date', 'rating', 'poster_url', 'tags'])
    
    try:
        df = pd.read_excel(file_path)
        return df
    except Exception as e:
        print(f"加载 {file_path} 失败: {e}")
        return pd.DataFrame(columns=['id', 'title', 'link', 'date', 'rating', 'poster_url', 'tags'])


def get_tag_movies_mapping(file_path):
    """获取标签与电影的映射
    
    参数:
        file_path: tags.xlsx 文件路径
    
    返回: 字典，键为标签，值为电影字典列表
    """
    df = load_tags_movies(file_path)
    
    if df.empty:
        return {}
    
    tag_mapping = {}
    
    for _, row in df.iterrows():
        tags_str = row.get('tags', '')
        
        if not tags_str or pd.isna(tags_str):
            continue
        
        # 处理斜杠分隔的标签
        tags = [t.strip() for t in str(tags_str).split('/')]
        
        movie_dict = {
            'id': row.get('id'),
            'title': row.get('title'),
            'link': row.get('link'),
            'date': row.get('date'),
            'rating': row.get('rating'),
            'poster_url': row.get('poster_url')
        }
        
        for tag in tags:
            if tag:
                if tag not in tag_mapping:
                    tag_mapping[tag] = []
                tag_mapping[tag].append(movie_dict)
    
    return tag_mapping


def stream_response_generator(message):
    """生成流式响应格式的消息
    
    参数:
        message: 要发送的消息
    
    返回: 格式化为 Server-Sent Events 的字符串
    """
    # 使用 Server-Sent Events 格式
    return f"data: {message}\n\n"
