# -*- coding: utf-8 -*-
"""Flask 电影管理系统 - 已重构，函数分离到 scripts/"""

import sys
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from flask import Flask, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from datetime import datetime
import time, pandas as pd, os

scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from douban_crawler import get_douban_movies, get_douban_movie_detail
from imdb_handler import get_imdb_tags, merge_movie_tags
from merge_tags import translate_imdb_tag
from data_handler import load_douban_config, convert_dataframe_to_dict_list, load_watched_movies, load_tags_movies, stream_response_generator

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROJECT_ROOT = os.path.dirname(__file__)
DOUBAN_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'douban_config.json')
if not os.path.exists(DOUBAN_CONFIG_FILE):
    DOUBAN_CONFIG_FILE = os.path.join(DATA_DIR, 'douban_config.json')

MOVIES_DOUBAN_FILE = os.path.join(DATA_DIR, 'watched.xlsx')
MPOSTERS_DIR = os.path.join(DATA_DIR, 'posters')

try:
    DOUBAN_USER_ID, DOUBAN_COOKIES = load_douban_config(DOUBAN_CONFIG_FILE)
    print(f" 已加载豆瓣配置")
except Exception as e:
    print(f"  加载豆瓣配置失败: {e}")
    DOUBAN_USER_ID = None
    DOUBAN_COOKIES = {}

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except ValueError as e:
        if "I/O operation on closed file" in str(e):
            sys.stderr.write(" ".join(map(str, args)) + "\n")

@app.before_request
def log_request_info():
    try:
        safe_print(f"\n[请求] {request.method} {request.path}")
    except:
        pass

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'}), 200

@app.route('/api/movies/update-douban', methods=['POST'])
def update_from_douban():
    try:
        safe_print("\n=== 从豆瓣更新电影 ===")
        if not DOUBAN_USER_ID:
            return jsonify({'error': '豆瓣配置未加载'}), 400
        
        existing_df = load_watched_movies(MOVIES_DOUBAN_FILE)
        existing_ids = set(existing_df['id'].astype(str).tolist()) if not existing_df.empty else set()
        safe_print(f"已有 {len(existing_ids)} 部电影")
        
        movies, new_count = get_douban_movies(DOUBAN_USER_ID, existing_ids=existing_ids)
        if not movies:
            return jsonify({'error': '未获取到电影数据'}), 500
        
        df_movies = pd.DataFrame(movies)
        df_movies = df_movies.rename(columns={'url': 'link', 'poster': 'poster_url'})
        df_movies.to_excel(MOVIES_DOUBAN_FILE, sheet_name='all', index=False)
        safe_print(f" 保存 {len(df_movies)} 部电影")
        
        return jsonify({'success': True, 'total': len(df_movies), 'new_count': new_count}), 200
    except Exception as e:
        safe_print(f" 错误: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/watched', methods=['GET'])
def get_watched_movies():
    try:
        df = load_watched_movies(MOVIES_DOUBAN_FILE)
        return jsonify(convert_dataframe_to_dict_list(df) if not df.empty else []), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/tags', methods=['GET'])
def get_tags_movies():
    try:
        df = load_tags_movies(os.path.join(DATA_DIR, 'tags.xlsx'))
        return jsonify(convert_dataframe_to_dict_list(df) if not df.empty else []), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/fetch-local', methods=['GET'])
def fetch_local_movies():
    try:
        watched_df = load_watched_movies(MOVIES_DOUBAN_FILE)
        tags_df = load_tags_movies(os.path.join(DATA_DIR, 'tags.xlsx'))
        return jsonify({'watched_count': len(watched_df), 'tags_count': len(tags_df), 'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posters/<filename>', methods=['GET'])
def get_poster(filename):
    try:
        if not filename.endswith('.jpg'):
            return jsonify({'error': 'Invalid file type'}), 400
        file_path = os.path.join(MPOSTERS_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Poster not found'}), 404
        return send_from_directory(MPOSTERS_DIR, filename, mimetype='image/jpeg')
    except Exception as e:
        safe_print(f" 获取海报失败: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/movies/update-imdb', methods=['POST'])
def update_from_imdb():
    def generate():
        try:
            safe_print("\n=== 从IMDb更新电影数据 ===")
            if not os.path.exists(MOVIES_DOUBAN_FILE):
                yield stream_response_generator({'message': f"文件不存在", 'success': False})
                return
            
            df_movies = pd.read_excel(MOVIES_DOUBAN_FILE, sheet_name='all')
            safe_print(f" 读取 {len(df_movies)} 部电影")
            
            if 'id' not in df_movies.columns or 'title' not in df_movies.columns:
                yield stream_response_generator({'message': "电影文件缺少必要列", 'success': False})
                return
            
            for col in ['genres', 'language', 'imdb_id', 'imdb_tags', 'tags', 'runtime']:
                if col not in df_movies.columns:
                    df_movies[col] = None
            
            total_movies = len(df_movies)
            processed_count = 0
            updated_count = 0
            
            yield stream_response_generator({'message': f'开始处理 {total_movies} 部电影...', 'progress': 0, 'total': total_movies, 'percentage': 0})
            
            for idx, row in df_movies.iterrows():
                title = row.get('title', 'Unknown')
                movie_url = row.get('link', '')
                processed_count += 1
                percentage = int((processed_count / total_movies) * 100)
                
                if processed_count % 5 == 0 or processed_count == 1:
                    yield stream_response_generator({'message': f'处理: {title}', 'progress': processed_count, 'total': total_movies, 'percentage': percentage})
                
                try:
                    has_genres = pd.notna(row.get('genres')) and str(row.get('genres')).strip()
                    has_imdb_id = pd.notna(row.get('imdb_id')) and str(row.get('imdb_id')).strip()
                    has_imdb_tags = pd.notna(row.get('imdb_tags')) and str(row.get('imdb_tags')).strip()
                    has_tags = pd.notna(row.get('tags')) and str(row.get('tags')).strip()
                    
                    if has_genres and has_imdb_id and has_imdb_tags and has_tags:
                        safe_print(f"[{processed_count}/{total_movies}]  跳过: {title}")
                        continue
                    
                    safe_print(f"[{processed_count}/{total_movies}] 处理: {title}")
                    
                    if not (has_genres and has_imdb_id) and movie_url:
                        imdb_id, genres, language, runtime = get_douban_movie_detail(movie_url, DOUBAN_COOKIES)
                        if genres and not has_genres:
                            df_movies.at[idx, 'genres'] = ', '.join(genres)
                            has_genres = True
                        if language:
                            df_movies.at[idx, 'language'] = language
                        if runtime:
                            df_movies.at[idx, 'runtime'] = runtime
                        if imdb_id and not has_imdb_id:
                            df_movies.at[idx, 'imdb_id'] = imdb_id
                            has_imdb_id = True
                    
                    if has_imdb_id and not has_imdb_tags:
                        time.sleep(0.5)
                        imdb_tags = get_imdb_tags(df_movies.at[idx, 'imdb_id'])
                        if imdb_tags:
                            df_movies.at[idx, 'imdb_tags'] = imdb_tags
                            has_imdb_tags = True
                    
                    if (has_genres or has_imdb_tags) and not has_tags:
                        genres_data = df_movies.at[idx, 'genres']
                        imdb_tags_data = df_movies.at[idx, 'imdb_tags']
                        
                        # 拆分并翻译 IMDb 标签
                        translated_imdb_tags = []
                        if imdb_tags_data and pd.notna(imdb_tags_data):
                            imdb_tag_list = [t.strip() for t in str(imdb_tags_data).split(',') if t.strip()]
                            for tag in imdb_tag_list:
                                translated = translate_imdb_tag(tag)
                                if translated:
                                    translated_imdb_tags.extend(translated)
                        
                        genres_list = [g.strip() for g in str(genres_data).split(',')] if pd.notna(genres_data) and str(genres_data).strip() else []
                        merged_tags = merge_movie_tags(genres_list, translated_imdb_tags)
                        if merged_tags:
                            df_movies.at[idx, 'tags'] = merged_tags.replace(', ', '/')
                    
                    updated_count += 1
                except Exception as e:
                    safe_print(f"   失败: {str(e)}")
                    continue
            
            tags_file = os.path.join(DATA_DIR, 'tags.xlsx')
            with pd.ExcelWriter(tags_file, engine='openpyxl') as writer:
                df_movies.to_excel(writer, sheet_name='all', index=False)
            safe_print(f" 保存成功")
            
            yield stream_response_generator({'message': '更新完成', 'success': True, 'updated_count': updated_count, 'total_count': total_movies, 'last_update': datetime.now().isoformat()})
        except Exception as e:
            import traceback
            safe_print(f" 错误: {str(e)}")
            traceback.print_exc()
            yield stream_response_generator({'message': f'错误: {str(e)}', 'success': False})
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
