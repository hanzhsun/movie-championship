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
import json
import threading
import queue
import mimetypes

scripts_path = os.path.join(os.path.dirname(__file__), 'scripts')
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)

from douban_crawler import get_douban_movies
from douban_detail import get_douban_movie_detail
from imdb_handler import get_imdb_tags, merge_movie_tags
from merge_tags import translate_imdb_tag
from data_handler import load_douban_config, convert_dataframe_to_dict_list, load_watched_movies, load_tags_movies, get_tag_movies_mapping, stream_response_generator

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*", "methods": ["GET", "POST", "OPTIONS"], "allow_headers": ["Content-Type", "Authorization"]}})

DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
PROJECT_ROOT = os.path.dirname(__file__)
DOUBAN_CONFIG_FILE = os.path.join(PROJECT_ROOT, 'douban_config.json')
if not os.path.exists(DOUBAN_CONFIG_FILE):
    DOUBAN_CONFIG_FILE = os.path.join(DATA_DIR, 'douban_config.json')

MOVIES_DOUBAN_FILE = os.path.join(DATA_DIR, 'watched.xlsx')
MOVIES_DOUBAN_CSV = os.path.join(DATA_DIR, 'watched.csv')
MPOSTERS_DIR = os.path.join(DATA_DIR, 'posters')
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(MPOSTERS_DIR, exist_ok=True)

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


@app.route('/favicon.ico')
def favicon():
    return '', 204

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
        
        debug = request.args.get('debug') == '1'
        force_full = request.args.get('force_full') == '1'
        existing_df = load_watched_movies(MOVIES_DOUBAN_FILE)
        existing_ids = set(existing_df['id'].astype(str).tolist()) if not existing_df.empty else set()
        safe_print(f"已有 {len(existing_ids)} 部电影")
        stream = request.args.get('stream') == '1'
        if stream:
            def generate():
                q = queue.Queue()

                def progress_cb(processed, total, new_count):
                    total_val = total or 0
                    percentage = int(processed / total_val * 100) if total_val else 0
                    message = f"已处理 {processed}/{total_val}" if total_val else f"已处理 {processed}"
                    q.put({"message": message, "progress": processed, "total": total_val, "percentage": percentage})

                def worker():
                    try:
                        movies, new_count = get_douban_movies(DOUBAN_USER_ID, existing_ids=existing_ids, force_full=force_full, cookies=DOUBAN_COOKIES, debug=debug, progress_cb=progress_cb)
                        if not movies and existing_ids and not force_full:
                            q.put({"message": "没有发现新电影，开始全量刷新..."})
                            movies, new_count = get_douban_movies(DOUBAN_USER_ID, existing_ids=existing_ids, force_full=True, cookies=DOUBAN_COOKIES, debug=debug, progress_cb=progress_cb)
                        if not movies:
                            q.put({"success": False, "done": True, "error": "No movies fetched. Check Douban user_id/cookies or access.", "message": "No movies fetched from Douban. Check user_id/cookies or access permissions.", "total": 0, "new_count": 0})
                            return

                        df_movies = pd.DataFrame(movies)
                        df_movies = df_movies.rename(columns={'url': 'link', 'poster': 'poster_url'})
                        try:
                            df_movies.to_excel(MOVIES_DOUBAN_FILE, sheet_name='all', index=False)
                            safe_print(f" ?? {len(df_movies)} ???")
                        except Exception as e:
                            safe_print(f"Excel write failed, falling back to CSV: {str(e)}")
                            df_movies.to_csv(MOVIES_DOUBAN_CSV, index=False, encoding='utf-8-sig')
                            safe_print(f" ?? {len(df_movies)} ??? (CSV)")

                        q.put({"success": True, "done": True, "total": len(df_movies), "new_count": new_count})
                    except Exception as e:
                        payload = {"success": False, "done": True, "error": f"Douban crawl failed: {str(e)}"}
                        debug_info = getattr(e, 'debug', None)
                        if debug and debug_info:
                            payload["debug"] = debug_info
                        q.put(payload)

                threading.Thread(target=worker, daemon=True).start()

                while True:
                    payload = q.get()
                    yield stream_response_generator(json.dumps(payload, ensure_ascii=False))
                    if payload.get('done'):
                        break

            return Response(generate(), mimetype='text/event-stream')
        try:
            movies, new_count = get_douban_movies(DOUBAN_USER_ID, existing_ids=existing_ids, force_full=force_full, cookies=DOUBAN_COOKIES, debug=debug)
            if not movies and existing_ids and not force_full:
                safe_print("No new movies found; retrying full refresh.")
                movies, new_count = get_douban_movies(DOUBAN_USER_ID, existing_ids=existing_ids, force_full=True, cookies=DOUBAN_COOKIES, debug=debug)
        except Exception as e:
            safe_print(f"Douban crawl error: {str(e)}")
            debug_info = getattr(e, 'debug', None)
            payload = {"error": f"Douban crawl failed: {str(e)}"}
            if debug and debug_info:
                payload["debug"] = debug_info
            return jsonify(payload), 502
        if not movies:
            safe_print("No movies fetched from Douban. Check user_id/cookies or access permissions.")
            return jsonify({
                "success": False,
                "error": "No movies fetched. Check Douban user_id/cookies or access.",
                "message": "No movies fetched from Douban. Check user_id/cookies or access permissions.",
                "total": 0,
                "new_count": 0
            }), 200
        
        df_movies = pd.DataFrame(movies)
        df_movies = df_movies.rename(columns={'url': 'link', 'poster': 'poster_url'})
        try:
            df_movies.to_excel(MOVIES_DOUBAN_FILE, sheet_name='all', index=False)
            safe_print(f" 保存 {len(df_movies)} 部电影")
        except Exception as e:
            safe_print(f"Excel write failed, falling back to CSV: {str(e)}")
            df_movies.to_csv(MOVIES_DOUBAN_CSV, index=False, encoding='utf-8-sig')
            safe_print(f" 保存 {len(df_movies)} 部电影 (CSV)")
        
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

@app.route('/api/tag-movies-mapping', methods=['GET'])
def get_tag_movies_mapping_api():
    try:
        mapping = get_tag_movies_mapping(os.path.join(DATA_DIR, 'tags.xlsx'))
        return jsonify({'success': True, 'mapping': mapping}), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/movies/fetch-local', methods=['GET'])
def fetch_local_movies():
    try:
        watched_df = load_watched_movies(MOVIES_DOUBAN_FILE)
        tags_df = load_tags_movies(os.path.join(DATA_DIR, 'tags.xlsx'))
        return jsonify({'watched_count': len(watched_df), 'tags_count': len(tags_df), 'success': True}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/posters/<path:filename>', methods=['GET'])
def get_poster(filename):
    try:
        base, ext = os.path.splitext(filename)
        candidates = []
        if ext:
            candidates.append(filename)
        if base:
            for ext in ('.jpg', '.jpeg', '.png', '.webp'):
                candidates.append(base + ext)
        for candidate in candidates:
            file_path = os.path.join(MPOSTERS_DIR, candidate)
            if os.path.exists(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                return send_from_directory(MPOSTERS_DIR, candidate, mimetype=mime or 'application/octet-stream')
        return jsonify({'error': 'Poster not found'}), 404
    except Exception as e:
        safe_print(f" ??????: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/movies/update-imdb', methods=['POST'])
def update_from_imdb():
    def generate():
        try:
            safe_print("\n=== 从IMDb更新电影数据 ===")
            if not os.path.exists(MOVIES_DOUBAN_FILE):
                yield stream_response_generator(json.dumps({'message': "文件不存在", 'success': False}, ensure_ascii=False))
                return
            
            df_movies = load_watched_movies(MOVIES_DOUBAN_FILE)
            safe_print(f" 读取 {len(df_movies)} 部电影")
            
            if 'id' not in df_movies.columns or 'title' not in df_movies.columns:
                yield stream_response_generator(json.dumps({'message': "电影文件缺少必要列", 'success': False}, ensure_ascii=False))
                return
            
            for col in ['genres', 'language', 'imdb_id', 'imdb_tags', 'tags', 'runtime', 'year']:
                if col not in df_movies.columns:
                    df_movies[col] = None
            
            total_movies = len(df_movies)
            processed_count = 0
            updated_count = 0
            
            yield stream_response_generator(json.dumps({'message': f'开始处理 {total_movies} 部电影...', 'progress': 0, 'total': total_movies, 'percentage': 0}, ensure_ascii=False))
            
            for idx, row in df_movies.iterrows():
                title = row.get('title', 'Unknown')
                movie_url = row.get('link', '')
                processed_count += 1
                percentage = int((processed_count / total_movies) * 100)
                
                if processed_count % 5 == 0 or processed_count == 1:
                    yield stream_response_generator(json.dumps({'message': f'处理: {title}', 'progress': processed_count, 'total': total_movies, 'percentage': percentage}, ensure_ascii=False))
                
                try:
                    has_genres = pd.notna(row.get('genres')) and str(row.get('genres')).strip()
                    has_imdb_id = pd.notna(row.get('imdb_id')) and str(row.get('imdb_id')).strip()
                    has_imdb_tags = pd.notna(row.get('imdb_tags')) and str(row.get('imdb_tags')).strip()
                    has_tags = pd.notna(row.get('tags')) and str(row.get('tags')).strip()
                    has_year = pd.notna(row.get('year')) and str(row.get('year')).strip()
                    has_language = pd.notna(row.get('language')) and str(row.get('language')).strip()
                    has_runtime = pd.notna(row.get('runtime')) and str(row.get('runtime')).strip()
                    
                    if has_genres and has_imdb_id and has_imdb_tags and has_tags and has_year and has_language and has_runtime:
                        safe_print(f"[{processed_count}/{total_movies}]  跳过: {title}")
                        continue
                    
                    safe_print(f"[{processed_count}/{total_movies}] 处理: {title}")
                    
                    if not (has_genres and has_imdb_id and has_year and has_language and has_runtime) and movie_url:
                        imdb_id, genres, language, runtime, year = get_douban_movie_detail(movie_url, DOUBAN_COOKIES)
                        if genres and not has_genres:
                            df_movies.at[idx, 'genres'] = ', '.join(genres)
                            has_genres = True
                        if language and not has_language:
                            df_movies.at[idx, 'language'] = language
                            has_language = True
                        if runtime and not has_runtime:
                            df_movies.at[idx, 'runtime'] = runtime
                            has_runtime = True
                        if year and not has_year:
                            df_movies.at[idx, 'year'] = year
                            has_year = True
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
            
            yield stream_response_generator(json.dumps({'message': '更新完成', 'success': True, 'updated_count': updated_count, 'total_count': total_movies, 'last_update': datetime.now().isoformat()}, ensure_ascii=False))
        except Exception as e:
            import traceback
            safe_print(f" 错误: {str(e)}")
            traceback.print_exc()
            yield stream_response_generator(json.dumps({'message': f'错误: {str(e)}', 'success': False}, ensure_ascii=False))
    
    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
