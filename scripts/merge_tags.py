# -*- coding: utf-8 -*-
"""
标签合并与翻译脚本

**处理函数：**
- `translate_imdb_tag(tag)`: 翻译单个 IMDb 标签为中文
  - 输入：IMDb 标签 (如 'Action Epic')
  - 输出：翻译后的中文列表 (如 ['动作', '史诗'])
  - 说明：支持组合标签拆分

- `split_and_translate_imdb_tags(imdb_tags_str)`: 拆分并翻译 IMDb 标签字符串
  - 输入：逗号分隔的标签字符串 (如 'Action, Thriller, Sci-Fi Epic')
  - 输出：翻译后的中文列表 (如 ['动作', '惊悚', '科幻', '史诗'])

- `merge_tags_to_movies_tags()`: 合并并保存到 movies_tags.xlsx
  - 读取来源：watched.xlsx / tags.xlsx
  - 输出：movies_tags.xlsx

- `merge_tags_to_common()`: 合并并保存到 movies_common.xlsx（向后兼容）

**包含的翻译字典：**
- 基础类型：100+ 种标签翻译
- 组合标签：支持如 'Action Epic' → '动作' + '史诗'

**注意：**
此脚本中的函数在 app.py 中也有实现，用于处理流式 API 请求。
该脚本主要用于独立执行标签合并和文件生成。

**使用示例：**
```bash
python merge_tags.py  # 生成 movies_tags.xlsx
```
"""
import sys
import io
import os

# 注意：在Flask流式响应中，不要重定向stdout/stderr，这会导致问题
# if sys.platform == 'win32':
#     sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
#     sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import pandas as pd
import json

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')

# IMDb标签翻译字典（仅包含实际存在的标签）
# 值为列表，表示翻译后的一个或多个标签（已支持tag拆分）
IMDB_TAG_TRANSLATION = {
    # 基础类型（不拆）
    'Action': ['动作'],
    'Adventure': ['冒险'],
    'Animation': ['动画'],
    'Anime': ['动画'],
    'Biography': ['传记'],
    'Comedy': ['喜剧'],
    'Crime': ['犯罪'],
    'Disaster': ['灾难'],
    'Documentary': ['纪录片'],
    'Family': ['家庭'],
    'History': ['历史'],
    'Horror': ['恐怖'],
    'Music': ['音乐'],
    'Mystery': ['悬疑'],
    'Romance': ['爱情'],
    'Sci-Fi': ['科幻'],
    'Science Fiction': ['科幻'],
    'Sport': ['运动'],
    'War': ['战争'],
    'Western': ['西部'],
    'Tragedy': ['悲剧'],

    # Epic
    'Epic': ['史诗'],
    'War Epic': ['战争', '史诗'],
    'Adventure Epic': ['冒险', '史诗'],
    'Romantic Epic': ['爱情', '史诗'],
    'Action Epic': ['动作', '史诗'],
    'Sci-Fi Epic': ['科幻', '史诗'],

    # Drama
    'Political Drama': ['政治'],
    'Cop Drama': ['警察'],
    'Period Drama': ['年代'],
    'Psychological Drama': ['心理'],
    'Teen Drama': ['青春'],
    'Docudrama': ['纪实'],

    # Adventure
    'Sea Adventure': ['海洋', '冒险'],
    'Desert Adventure': ['沙漠', '冒险'],
    'Mountain Adventure': ['山地', '冒险'],
    'Globetrotting Adventure': ['环球', '冒险'],
    'Dinosaur Adventure': ['恐龙', '冒险'],

    # Romance / Comedy
    'Romantic Comedy': ['爱情', '喜剧'],
    'Teen Comedy': ['青春', '喜剧'],
    'Concept Comedy': ['概念', '喜剧'],
    'Quirky Comedy': ['怪诞', '喜剧'],
    'High-Concept Comedy': ['高概念', '喜剧', '概念'],
    'Dark Comedy': ['黑色喜剧', '喜剧', '黑暗'],
    'Dark Romance': ['黑暗', '爱情'],
    'Tragic Romance': ['悲剧', '爱情'],
    'Steamy Romance': ['激情', '爱情'],
    'Teen Romance': ['青春', '爱情'],
    'Feel-Good Romance': ['温暖', '爱情'],

    # 惊悚
    'Thriller': ['惊悚'],
    'Political Thriller': ['政治', '惊悚'],
    'Psychological Thriller': ['心理', '惊悚'],
    'Conspiracy Thriller': ['阴谋', '惊悚'],
    'Legal Thriller': ['律政', '惊悚'],
    'Cyber Thriller': ['网络', '惊悚'],

    # 恐怖
    'Body Horror': ['肉体', '恐怖'],
    'Psychological Horror': ['心理', '恐怖'],
    'Found Footage Horror': ['伪纪录片', '恐怖'],
    'Monster Horror': ['怪物', '恐怖'],
    'Splatter Horror': ['血浆', '恐怖'],
    'Vampire Horror': ['吸血鬼', '恐怖'],
    'Zombie Horror': ['僵尸', '恐怖'],
    'Witch Horror': ['女巫', '恐怖'],
    'Folk Horror': ['民俗', '恐怖'],
    'Supernatural Horror': ['超自然', '恐怖'],
    'Teen Horror': ['青春', '恐怖'],
    'B-Horror': ['B级', '恐怖'],

    # 动作 / 犯罪
    'Car Action': ['汽车', '动作'],
    'Martial Arts': ['武术'],
    'Gun Fu': ['枪斗'],
    'Spy': ['间谍'],
    'Heist': ['劫案'],
    'Caper': ['怪盗'],
    'One-Person Army Action': ['一人成军'],

    # 科幻
    'Alien Invasion': ['外星入侵'],
    'Dystopian Sci': ['反乌托邦', '科幻'],
    'Dystopian Sci-Fi': ['反乌托邦', '科幻'],
    'Space Sci': ['太空', '科幻'],
    'Space Sci-Fi': ['太空', '科幻'],
    'Time Travel': ['时间旅行'],
    'Steampunk': ['蒸汽朋克'],

    # 奇幻
    'Fantasy': ['奇幻'],
    'Supernatural Fantasy': ['超自然', '奇幻'],
    'Dark Fantasy': ['黑暗', '奇幻'],

    'Drug Crime': ['毒贩', '犯罪'],
    'True Crime': ['真实犯罪', '犯罪'],

    # 其他
    'Whodunnit': ['推理'],
    'Detective': ['侦探'],
    'Serial Killer': ['连环杀手'],
    'Hard-boiled Detective': ['硬汉', '侦探'],
    'Police Procedural': ['刑侦'],
    'Suspense Mystery': ['悬疑', '推理'],
    'Hand-Drawn Animation': ['手绘', '动画'],
    'Contemporary Western': ['现代西部'],
    'Kaiju': ['怪兽'],
    'Survival': ['生存'],
    'Road Trip': ['公路'],
    'Quest': ['使命'],
    'Fairy Tale': ['童话'],
    'Slice of Life': ['生活'],
    'Satire': ['讽刺'],
    'Coming-of-Age': ['成长'],
    'Motorsport': ['赛车'],
}

def translate_imdb_tag(tag):
    """翻译IMDb标签为中文列表（支持tag拆分）"""
    tag = tag.strip()
    
    # 忽略语言标签
    language_tags = {
        'English', 'Japanese', 'Chinese', 'French', 'German', 'Spanish', 'Italian',
        'Korean', 'Russian', 'Portuguese', 'Hindi', 'Arabic', 'Turkish', 'Polish',
        'Dutch', 'Swedish', 'Norwegian', 'Danish', 'Finnish', 'Greek', 'Hebrew',
        'Thai', 'Vietnamese', 'Indonesian', 'Malay', 'Tagalog', 'Mandarin',
        'Cantonese', 'Tamil'
    }
    if tag in language_tags:
        return []  # 返回空列表表示应该被忽略
    
    # 直接匹配
    if tag in IMDB_TAG_TRANSLATION:
        return IMDB_TAG_TRANSLATION[tag]  # 返回列表
    
    # 如果已经是中文，直接返回
    if any('\u4e00' <= char <= '\u9fff' for char in tag):
        return [tag]
    
    # 未找到翻译，返回空列表（不保留未翻译的英文标签）
    return []

def merge_tags_to_movies_tags():
    """合并genres和imdb_tags到tags列，保存到movies_tags.xlsx"""
    movies_file = os.path.join(DATA_DIR, 'movies_common.xlsx')
    print(f"[merge_tags] 开始合并标签...")
    print(f"[merge_tags] 读取文件: {movies_file}")
    
    try:
        df = pd.read_excel(movies_file, sheet_name='all')
        print(f"[merge_tags] 共 {len(df)} 部电影")
        print(f"[merge_tags] 列名: {list(df.columns)}")
    except Exception as e:
        print(f"[merge_tags] 读取文件失败: {e}")
        import traceback
        traceback.print_exc()
        raise  # 重新抛出异常，让调用者知道出错了
    
    # 检查必要的列
    if 'genres' not in df.columns:
        print("警告: 文件中没有 'genres' 列")
        df['genres'] = ''
    
    if 'imdb_tags' not in df.columns:
        print("警告: 文件中没有 'imdb_tags' 列")
        df['imdb_tags'] = ''
    
    # 创建tags列
    df['tags'] = ''
    
    for idx, row in df.iterrows():
        title = row.get('title', 'N/A')
        genres = row.get('genres', '')
        imdb_tags = row.get('imdb_tags', '')
        
        # 收集所有标签
        all_tags = []
        
        # 处理genres（已经是中文）
        if genres and pd.notna(genres):
            genres_str = str(genres).strip()
            if genres_str:
                # genres可能是逗号分隔的字符串
                genre_list = [g.strip() for g in genres_str.split(',') if g.strip()]
                all_tags.extend(genre_list)
        
        # 处理imdb_tags（需要翻译，支持拆分）
        if imdb_tags and pd.notna(imdb_tags):
            imdb_tags_str = str(imdb_tags).strip()
            if imdb_tags_str:
                # imdb_tags是逗号分隔的字符串
                imdb_tag_list = [t.strip() for t in imdb_tags_str.split(',') if t.strip()]
                # 翻译每个标签，获得列表，展开后过滤掉空列表
                for t in imdb_tag_list:
                    translated_tags = translate_imdb_tag(t)  # 返回列表
                    if translated_tags:  # 如果翻译列表不为空
                        all_tags.extend(translated_tags)
        
        # 去重并保持顺序
        unique_tags = []
        seen = set()
        for tag in all_tags:
            if tag and tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        # 保存为/分隔的字符串（前端使用split('/')）
        df.at[idx, 'tags'] = '/'.join(unique_tags) if unique_tags else ''

        
        if idx < 5:  # 打印前5个示例
            print(f"[{idx+1}] {title}: tags={df.at[idx, 'tags']}, country={row.get('country', 'N/A')}")
    
    # 确保所有列都被保留（包括country, language, runtime等）
    # df已经包含了所有列，只需要确保tags列被正确设置
    
    # 生成 tag -> movie IDs 映射（用于前端快速查找）
    print(f"[merge_tags] 生成 tag -> movies 映射...")
    tag_movies_mapping = {}
    for idx, row in df.iterrows():
        movie_id = str(row.get('id', ''))
        if not movie_id or pd.isna(movie_id):
            continue
        
        tags_str = row.get('tags', '')
        if tags_str and pd.notna(tags_str):
            tags = str(tags_str).split('/')
            for tag in tags:
                tag = tag.strip()
                if tag:
                    if tag not in tag_movies_mapping:
                        tag_movies_mapping[tag] = []
                    tag_movies_mapping[tag].append(movie_id)
    
    # 保存 tag -> movies 映射为 JSON 文件
    mapping_file = os.path.join(DATA_DIR, 'tag_movies_mapping.json')
    try:
        with open(mapping_file, 'w', encoding='utf-8') as f:
            json.dump(tag_movies_mapping, f, ensure_ascii=False, indent=2)
        print(f"[merge_tags] ✓ 成功创建 tag -> movies 映射文件: {mapping_file}")
        print(f"[merge_tags] 共 {len(tag_movies_mapping)} 个不同的 tag")
    except Exception as e:
        print(f"[merge_tags] 保存映射文件失败: {e}")
        import traceback
        traceback.print_exc()
        # 不抛出异常，因为这不是关键功能
    
    # 保存到movies_tags.xlsx
    output_file = os.path.join(DATA_DIR, 'movies_tags.xlsx')
    print(f"[merge_tags] 保存到: {output_file}")
    print(f"[merge_tags] 列名: {list(df.columns)}")
    print(f"[merge_tags] tags列示例（前3个）: {df['tags'].head(3).tolist()}")
    
    try:
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='all', index=False)
        print(f"[merge_tags] ✓ 成功创建 {output_file}，包含 {len(df)} 条记录，{len(df.columns)} 列")
    except Exception as e:
        print(f"[merge_tags] 保存失败: {e}")
        import traceback
        traceback.print_exc()
        raise  # 重新抛出异常

def merge_tags_to_common():
    """合并genres和imdb_tags到tags列，保存到movies_common.xlsx（用于向后兼容）"""
    movies_file = os.path.join(DATA_DIR, 'movies_common.xlsx')
    print(f"读取文件: {movies_file}")
    
    try:
        df = pd.read_excel(movies_file, sheet_name='all')
        print(f"共 {len(df)} 部电影")
    except Exception as e:
        print(f"读取文件失败: {e}")
        return
    
    # 检查必要的列
    if 'genres' not in df.columns:
        print("警告: 文件中没有 'genres' 列")
        df['genres'] = ''
    
    if 'imdb_tags' not in df.columns:
        print("警告: 文件中没有 'imdb_tags' 列")
        df['imdb_tags'] = ''
    
    # 创建tags列
    df['tags'] = ''
    
    for idx, row in df.iterrows():
        genres = row.get('genres', '')
        imdb_tags = row.get('imdb_tags', '')
        
        # 收集所有标签
        all_tags = []
        
        # 处理genres（已经是中文）
        if genres and pd.notna(genres):
            genres_str = str(genres).strip()
            if genres_str:
                genre_list = [g.strip() for g in genres_str.split(',') if g.strip()]
                all_tags.extend(genre_list)
        
        # 处理imdb_tags（需要翻译，支持拆分）
        if imdb_tags and pd.notna(imdb_tags):
            imdb_tags_str = str(imdb_tags).strip()
            if imdb_tags_str:
                imdb_tag_list = [t.strip() for t in imdb_tags_str.split(',') if t.strip()]
                # 翻译每个标签，获得列表，展开后过滤掉空列表
                for t in imdb_tag_list:
                    translated_tags = translate_imdb_tag(t)  # 返回列表
                    if translated_tags:  # 如果翻译列表不为空
                        all_tags.extend(translated_tags)
        
        # 去重并保持顺序
        unique_tags = []
        seen = set()
        for tag in all_tags:
            if tag and tag not in seen:
                unique_tags.append(tag)
                seen.add(tag)
        
        # 保存为逗号分隔的字符串
        df.at[idx, 'tags'] = ', '.join(unique_tags) if unique_tags else ''
    
    # 保存回movies_common.xlsx
    print(f"\n保存到: {movies_file}")
    
    try:
        with pd.ExcelWriter(movies_file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='all', index=False)
        print(f"✓ 成功更新 {movies_file}，包含 {len(df)} 条记录")
    except Exception as e:
        print(f"保存失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    # 默认合并到movies_tags.xlsx
    merge_tags_to_movies_tags()
    # 也可以合并到movies_common.xlsx（取消注释下面这行）
    # merge_tags_to_common()
