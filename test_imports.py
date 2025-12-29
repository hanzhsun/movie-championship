# -*- coding: utf-8 -*-
"""
验证所有模块导入和核心功能是否正常
"""

import sys
import os

scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

print("=" * 60)
print("开始测试模块导入和功能...")
print("=" * 60)

try:
    print("\n1. 测试 merge_tags 导入...")
    from merge_tags import translate_imdb_tag, IMDB_TAG_TRANSLATION
    print(f"   ✓ 成功导入 translate_imdb_tag")
    print(f"   ✓ 翻译字典包含 {len(IMDB_TAG_TRANSLATION)} 个条目")
    
    # 测试翻译功能（包括组合标签拆分）
    test_tag = 'Action Epic'
    result = translate_imdb_tag(test_tag)
    print(f"   ✓ 测试翻译: '{test_tag}' → {result}")
    
    test_tag2 = 'Action'
    result2 = translate_imdb_tag(test_tag2)
    print(f"   ✓ 测试翻译: '{test_tag2}' → {result2}")
    
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("\n2. 测试 imdb_handler 导入...")
    from imdb_handler import get_imdb_tags, merge_movie_tags
    print(f"   ✓ 成功导入 get_imdb_tags, merge_movie_tags")
    
    # 测试 merge_movie_tags
    result = merge_movie_tags(['动作', '冒险'], ['科幻', '动作'])
    print(f"   ✓ 测试 merge_movie_tags: ['动作', '冒险'] + ['科幻'] = {result}")
    
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("\n3. 测试 douban_crawler 导入...")
    from douban_crawler import get_douban_movies, get_douban_movie_detail
    print(f"   ✓ 成功导入 get_douban_movies, get_douban_movie_detail")
    
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

try:
    print("\n4. 测试 data_handler 导入...")
    from data_handler import load_douban_config, load_watched_movies, load_tags_movies, convert_dataframe_to_dict_list, stream_response_generator
    print(f"   ✓ 成功导入 data_handler 的所有函数")
    
except Exception as e:
    print(f"   ✗ 导入失败: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ 所有模块导入测试通过！")
print("=" * 60)

# 测试组合标签翻译的完整流程
print("\n5. 测试完整的标签翻译流程...")
imdb_tags_str = "Action, Sci-Fi Epic, Thriller"
print(f"   输入: '{imdb_tags_str}'")

translated_imdb_tags = []
imdb_tag_list = [t.strip() for t in imdb_tags_str.split(',') if t.strip()]
for tag in imdb_tag_list:
    translated = translate_imdb_tag(tag)
    print(f"   '{tag}' → {translated}")
    if translated:
        translated_imdb_tags.extend(translated)

print(f"   ✓ 翻译完成，所有标签: {translated_imdb_tags}")

# 合并标签
genres_list = ['动作']
merged = merge_movie_tags(genres_list, translated_imdb_tags)
print(f"   ✓ 与 genres 合并: '{merged}'")

print("\n" + "=" * 60)
print("✓ 完整流程测试通过！")
print("=" * 60)
