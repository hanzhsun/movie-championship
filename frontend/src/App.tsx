import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import axios from 'axios';
import { Film, Clock, Heart, Layers, Trophy, ChevronDown } from 'lucide-react';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

interface DoubanMovie {
  id: string;
  title: string;
  url: string;
  date: string;
  rating?: number;
  poster?: string;
  genres?: string[];
  country?: string;
  language?: string; // 语言
  year?: number;
  tags?: string;
  imdb_id?: string;
  imdb_tags?: string;
  runtime?: number; // 片长（分钟）
}

interface WeeklyLog {
  week: number;
  date: string;
  movies: DoubanMovie[];
}

interface PieChartData {
  language: string;
  count: number;
  movies: string[];
}

interface LineChartData {
  year: number;
  count: number;
  movies: string[];
}

interface Genre {
  id: string;
  tag: string;
  movies: DoubanMovie[];
  winner?: DoubanMovie;
}

// 饼状图组件
const PieChart: React.FC<{ data: PieChartData[]; size?: number }> = ({ data, size = 400 }) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const radius = size / 2.5;
  const centerX = size / 2;
  const centerY = size / 2;
  
  let currentAngle = -Math.PI / 2;
  const total = data.reduce((sum, item) => sum + item.count, 0);
  
  // 使用柔和的绿色系颜色
  const colors = ['#a7f3d0', '#86efac', '#6ee7b7', '#34d399', '#10b981', '#059669', '#047857'];
  
  return (
    <div ref={containerRef} className="relative w-full flex flex-col md:flex-row items-start gap-8">
      <svg width={size} height={size} className="flex-shrink-0">
        {data.map((item, index) => {
          const sliceAngle = (item.count / total) * 2 * Math.PI;
          const startAngle = currentAngle;
          const endAngle = currentAngle + sliceAngle;
          
          const x1 = centerX + radius * Math.cos(startAngle);
          const y1 = centerY + radius * Math.sin(startAngle);
          const x2 = centerX + radius * Math.cos(endAngle);
          const y2 = centerY + radius * Math.sin(endAngle);
          const largeArcFlag = sliceAngle > Math.PI ? 1 : 0;
          
          const pathData = [
            `M ${centerX} ${centerY}`,
            `L ${x1} ${y1}`,
            `A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2}`,
            'Z'
          ].join(' ');
          
          currentAngle += sliceAngle;
          
          const color = colors[index % colors.length];
          const isHovered = hoveredIndex === index;
          
          return (
            <g key={index}>
              <path
                d={pathData}
                fill={color}
                stroke="white"
                strokeWidth="2"
                className="cursor-pointer transition-opacity"
                style={{ opacity: isHovered ? 1 : hoveredIndex === null ? 1 : 0.3 }}
                onMouseEnter={() => setHoveredIndex(index)}
                onMouseLeave={() => setHoveredIndex(null)}
              />
            </g>
          );
        })}
      </svg>
      {/* Legend: 颜色标识 + 国家+百分比（加粗）+ 电影名字 */}
      <div className="flex flex-col gap-4 flex-1 min-w-0">
        {data.map((item, index) => {
          const percentage = ((item.count / total) * 100).toFixed(1);
          const isHovered = hoveredIndex === index;
          const color = colors[index % colors.length];
          return (
            <div 
              key={index} 
              className={`transition-all ${
                isHovered 
                  ? 'scale-105 opacity-100' 
                  : hoveredIndex === null 
                    ? 'opacity-100' 
                    : 'opacity-30'
              }`}
            >
              <div className="font-bold text-base text-slate-700 mb-2 flex items-center gap-2">
                <span 
                  className="inline-block w-4 h-4 rounded-sm flex-shrink-0" 
                  style={{ backgroundColor: color }}
                />
                <span>{item.language}{percentage}%</span>
              </div>
              <div className="flex flex-wrap gap-2 ml-6">
                {item.movies.slice(0, 7).map((movie, idx) => (
                  <span 
                    key={idx}
                    className="text-sm text-slate-600 bg-green-50/50 px-3 py-2 rounded border border-green-100"
                  >
                    {movie}
                  </span>
                ))}
                {item.movies.length > 7 && (
                  <span className="text-sm text-slate-400 bg-green-50/50 px-3 py-2 rounded border border-green-100">
                    ……（共{item.movies.length}部）
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// 折线图组件
const LineChart: React.FC<{ data: LineChartData[] }> = ({ data }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerWidth, setContainerWidth] = useState(800);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; movies: string[] } | null>(null);
  
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth);
      }
    };
    
    updateWidth();
    window.addEventListener('resize', updateWidth);
    return () => window.removeEventListener('resize', updateWidth);
  }, []);
  
  if (data.length === 0) return null;
  
  const width = containerWidth;
  const height = 300;
  const padding = { top: 20, right: 20, bottom: 40, left: 60 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;
  
  const years = data.map(d => d.year);
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const maxCount = Math.max(...data.map(d => d.count));
  
  const points = data.map((item, index) => {
    // 计算X坐标，第一个点稍微往后挪，避免和Y轴重合
    let x = padding.left + ((item.year - minYear) / (maxYear - minYear || 1)) * chartWidth;
    if (index === 0 && data.length > 1) {
      // 第一个点向右偏移，至少距离Y轴20px
      x = Math.max(padding.left + 20, x);
    }
    const y = padding.top + chartHeight - (item.count / maxCount) * chartHeight;
    return { ...item, x, y, index };
  });
  
  const pathData = points.map((point, index) => 
    `${index === 0 ? 'M' : 'L'} ${point.x} ${point.y}`
  ).join(' ');
  
  return (
    <div ref={containerRef} className="w-full relative">
      <h3 className="text-lg font-semibold mb-4 text-center text-emerald-900">Years and Years</h3>
      <svg width={width} height={height} className="border border-green-100 rounded-lg bg-white">
        <g>
          {/* Y轴 */}
          <line
            x1={padding.left}
            y1={padding.top}
            x2={padding.left}
            y2={padding.top + chartHeight}
            stroke="#94a3b8"
            strokeWidth="1"
          />
          {/* X轴 */}
          <line
            x1={padding.left}
            y1={padding.top + chartHeight}
            x2={padding.left + chartWidth}
            y2={padding.top + chartHeight}
            stroke="#94a3b8"
            strokeWidth="1"
          />
          {/* Y轴刻度 */}
          {[0, 1, 2, 3, 4, 5].map((tick) => {
            const yValue = (tick / 5) * maxCount;
            const y = padding.top + chartHeight - (yValue / maxCount) * chartHeight;
            return (
              <g key={tick}>
                <line
                  x1={padding.left - 5}
                  y1={y}
                  x2={padding.left}
                  y2={y}
                  stroke="#94a3b8"
                  strokeWidth="1"
                />
                <text
                  x={padding.left - 10}
                  y={y}
                  textAnchor="end"
                  dominantBaseline="middle"
                  className="text-xs fill-slate-500"
                >
                  {Math.round(yValue)}
                </text>
              </g>
            );
          })}
          {/* X轴刻度（年份） */}
          {points.map((point) => (
            <g key={`x-tick-${point.year}`}>
              <line
                x1={point.x}
                y1={padding.top + chartHeight}
                x2={point.x}
                y2={padding.top + chartHeight + 5}
                stroke="#94a3b8"
                strokeWidth="1"
              />
              <text
                x={point.x}
                y={padding.top + chartHeight + 20}
                textAnchor="middle"
                className="text-xs fill-slate-500"
              >
                {point.year}
              </text>
            </g>
          ))}
          <path
            d={pathData}
            fill="none"
            stroke="#10b981"
            strokeWidth="2"
            className="drop-shadow-sm"
          />
          {points.map((point) => (
            <g key={point.year}>
              <circle
                cx={point.x}
                cy={point.y}
                r="6"
                fill="#10b981"
                stroke="white"
                strokeWidth="2"
                className="cursor-pointer hover:r-8 transition-all"
                onMouseEnter={() => {
                  if (point.count > 1 && point.movies.length > 0) {
                    setHoveredPoint({ x: point.x, y: point.y, movies: point.movies });
                  }
                }}
                onMouseLeave={() => setHoveredPoint(null)}
              />
              {point.count === 1 && (
                <text
                  x={point.x}
                  y={point.y - 8}
                  textAnchor="middle"
                  className="text-xs fill-slate-400 pointer-events-none font-medium"
                >
                  {point.movies[0].split('').map((char, charIdx) => {
                    const totalChars = point.movies[0].length;
                    return (
                      <tspan
                        key={charIdx}
                        x={point.x}
                        dy={charIdx === 0 ? `-${(totalChars - 1) * 1}em` : '1em'}
                      >
                        {char}
                      </tspan>
                    );
                  })}
                </text>
              )}
            </g>
          ))}
        </g>
      </svg>
      {/* 自定义Tooltip */}
      {hoveredPoint && (
        <div
          className="absolute bg-emerald-600 text-white text-xs rounded-lg p-3 shadow-xl z-50 pointer-events-none"
          style={{
            left: `${(hoveredPoint.x / width) * 100}%`,
            top: `${((hoveredPoint.y - 80) / height) * 100}%`,
            transform: 'translateX(-50%)',
          }}
        >
          <div className="space-y-1">
            {hoveredPoint.movies.slice(0, 5).map((movie, idx) => (
              <div key={idx} className="text-emerald-50 whitespace-nowrap">
                • {movie}
              </div>
            ))}
            {hoveredPoint.movies.length > 5 && (
              <div className="text-emerald-50 whitespace-nowrap">
                ……（共{hoveredPoint.movies.length}部）
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const MovieRewindApp = () => {
  const [activeTab, setActiveTab] = useState<'overview' | 'calendar'>('calendar');
  const [selectedYear, setSelectedYear] = useState<number>(2025);
  const [doubanMovies, setDoubanMovies] = useState<DoubanMovie[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingDouban, setLoadingDouban] = useState(false);
  const [loadingImdb, setLoadingImdb] = useState(false);
  const [selectedMovies, setSelectedMovies] = useState<Set<string>>(new Set());
  const [trophyMovies, setTrophyMovies] = useState<Set<string>>(new Set());
  const [genreWinners, setGenreWinners] = useState<Map<string, string>>(new Map());
  const [tagMoviesMapping, setTagMoviesMapping] = useState<Map<string, string[]>>(new Map());

  // 加载genre winners
  useEffect(() => {
    try {
      const saved = localStorage.getItem('genreWinners');
      if (saved) {
        const winners = new Map<string, string>(JSON.parse(saved) as [string, string][]);
        setGenreWinners(winners);
      }
    } catch (e) {
      // 加载失败，继续使用默认值
    }
  }, []);

  // 从豆瓣更新
  const refreshFromDouban = async () => {
    setLoadingDouban(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/movies/update-douban`);
      if (response.data.success) {
        await fetchLocalMovies();
        alert(`更新成功：新增 ${response.data.new_count} 部电影`);
      }
    } catch (error) {
      alert('更新失败，请检查后端服务');
    } finally {
      setLoadingDouban(false);
    }
  };

  // 从IMDb更新（带进度显示）
  const [updateProgress, setUpdateProgress] = useState<{
    message: string;
    progress: number;
    total: number;
    percentage: number;
  } | null>(null);

  const refreshFromImdb = async () => {
    setLoadingImdb(true);
    setUpdateProgress({ message: '开始更新...', progress: 0, total: 0, percentage: 0 });
    
    try {
      const url = `${API_BASE_URL}/api/movies/update-imdb`;
      
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let finalResult: any = null;
      
      if (!reader) {
        throw new Error('无法读取响应流');
      }
      
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // 保留最后一个不完整的行
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(5));
              
              // 如果是进度更新
              if (data.message !== undefined) {
                if (data.progress !== undefined && data.total !== undefined) {
                  setUpdateProgress({
                    message: data.message,
                    progress: data.progress,
                    total: data.total,
                    percentage: data.percentage || (data.total > 0 ? Math.round((data.progress / data.total) * 100) : 0)
                  });
                } else {
                  // 只有消息，没有进度
                  setUpdateProgress(prev => prev ? {
                    ...prev,
                    message: data.message
                  } : null);
                }
              }
              
              // 如果是最终结果
              if (data.success !== undefined) {
                finalResult = data;
              }
            } catch (e) {
              // 解析失败，继续
            }
          }
        }
      }
      
      if (finalResult) {
        if (finalResult.success) {
          setUpdateProgress(null);
          await fetchLocalMovies();
        } else {
          setUpdateProgress(null);
          alert(`更新失败: ${finalResult.error || '未知错误'}`);
        }
      } else {
        setUpdateProgress(null);
      }
    } catch (error: any) {
      setUpdateProgress(null);
      if (error.message) {
        alert(`更新失败: ${error.message}`);
      } else {
        alert('更新失败，请检查后端服务');
      }
    } finally {
      setLoadingImdb(false);
    }
  };

  // 获取本地电影数据
  const fetchLocalMovies = useCallback(async () => {
    setLoading(true);
    try {
      const endpoint = activeTab === 'calendar' ? '/api/movies/watched' : '/api/movies/tags';
      const response = await axios.get(`${API_BASE_URL}${endpoint}`);
      if (response.data?.success && response.data?.movies) {
        setDoubanMovies(response.data.movies);
      } else {
        setDoubanMovies([]);
      }
    } catch (error) {
      setDoubanMovies([]);
    } finally {
      setLoading(false);
    }
  }, [activeTab]);

  // 加载 tag -> movies 映射
  const fetchTagMoviesMapping = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/tag-movies-mapping`);
      if (response.data?.success && response.data?.mapping) {
        const mapping = new Map<string, string[]>();
        Object.entries(response.data.mapping).forEach(([tag, movieIds]: [string, any]) => {
          mapping.set(tag, Array.isArray(movieIds) ? movieIds : []);
        });
        setTagMoviesMapping(mapping);
      }
    } catch (error) {
      // 如果映射文件不存在，继续使用计算方式
    }
  };

  // 页面加载时自动读取数据（如果movies_common已存在，直接展示）
  useEffect(() => {
    const loadData = async () => {
      await fetchLocalMovies();
      // 只有在overview标签页时才加载tag映射
      if (activeTab === 'overview') {
        fetchTagMoviesMapping();
      }
    };
    loadData();
  }, [activeTab, fetchLocalMovies]);

  // 按年份过滤电影
  const filteredMovies = useMemo(() => {
    if (!doubanMovies || doubanMovies.length === 0) return [];
    return doubanMovies.filter(movie => {
      if (!movie.date) return false;
      const date = new Date(movie.date);
      return date.getFullYear() === selectedYear;
    });
  }, [doubanMovies, selectedYear]);

  // 计算周度记录
  const weeklyLog = useMemo(() => {
    if (!filteredMovies || filteredMovies.length === 0) return [];
    
    const logs: WeeklyLog[] = [];
    const moviesByWeek = new Map<number, DoubanMovie[]>();
    
    filteredMovies.forEach(movie => {
      if (!movie.date) return;
      const date = new Date(movie.date);
      const week = getWeekNumber(date);
      if (!moviesByWeek.has(week)) {
        moviesByWeek.set(week, []);
      }
      moviesByWeek.get(week)!.push(movie);
    });
    
    moviesByWeek.forEach((movies, week) => {
      movies.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
      logs.push({
        week,
        date: movies[0].date,
        movies
      });
    });
    
    logs.sort((a, b) => a.week - b.week); // 正序显示
    return logs;
  }, [filteredMovies]);

  // 计算饼状图数据（语言分布）
  const pieChartData = useMemo(() => {
    const languageMap = new Map<string, { count: number; movies: string[] }>();
    
    filteredMovies.forEach(movie => {
      if (movie.language) {
        // 语言可能用 / 分隔，但我们只取第一个（已经在后端处理过）
        const language = movie.language.trim();
        if (language) {
          if (!languageMap.has(language)) {
            languageMap.set(language, { count: 0, movies: [] });
          }
          const data = languageMap.get(language)!;
          data.count++;
          if (!data.movies.includes(movie.title)) {
            data.movies.push(movie.title);
          }
        }
      }
    });
    
    return Array.from(languageMap.entries())
      .map(([language, data]) => ({
        language,
        count: data.count,
        movies: data.movies
      }))
      .sort((a, b) => b.count - a.count);
  }, [filteredMovies]);

  // 计算折线图数据（年份分布）
  const lineChartData = useMemo(() => {
    const yearMap = new Map<number, { count: number; movies: string[] }>();
    
    filteredMovies.forEach(movie => {
      if (movie.year) {
        if (!yearMap.has(movie.year)) {
          yearMap.set(movie.year, { count: 0, movies: [] });
        }
        const data = yearMap.get(movie.year)!;
        data.count++;
        data.movies.push(movie.title);
      }
    });
    
    return Array.from(yearMap.entries())
      .map(([year, data]) => ({
        year,
        count: data.count,
        movies: data.movies
      }))
      .sort((a, b) => a.year - b.year);
  }, [filteredMovies]);

  // 计算类型数据
  // 计算所有tag及其对应的电影（包括只有一部电影的tag）
  // 优先使用预加载的映射，如果没有则实时计算
  const allTags = useMemo(() => {
    const tagMap = new Map<string, DoubanMovie[]>();
    
    // 如果映射已加载且不为空，使用映射
    if (tagMoviesMapping.size > 0) {
      // 创建 movie ID -> movie 的映射
      const movieMap = new Map<string, DoubanMovie>();
      filteredMovies.forEach(movie => {
        if (movie.id) {
          movieMap.set(movie.id, movie);
        }
      });
      
      // 使用预加载的映射
      tagMoviesMapping.forEach((movieIds, tag) => {
        const movies: DoubanMovie[] = [];
        movieIds.forEach((movieId: string) => {
          const movie = movieMap.get(movieId);
          if (movie) {
            movies.push(movie);
          }
        });
        if (movies.length > 0) {
          tagMap.set(tag, movies);
        }
      });
    } else {
      // 回退到实时计算
      filteredMovies.forEach(movie => {
        const tags = movie.tags ? movie.tags.split('/').map(t => t.trim()).filter(t => t) : [];
        tags.forEach(tag => {
          if (!tagMap.has(tag)) {
            tagMap.set(tag, []);
          }
          tagMap.get(tag)!.push(movie);
        });
      });
    }
    
    return tagMap;
  }, [filteredMovies, tagMoviesMapping]);

  // 类型版图：只显示有多部电影的tag
  const genres = useMemo(() => {
    return Array.from(allTags.entries())
      .filter(([tag, movies]) => movies.length > 1) // 过滤掉只有一部电影的tag
      .map(([tag, movies]) => {
        const genre: Genre = {
          id: `tag-${tag}`,
          tag,
          movies,
          winner: undefined
        };
        
        // 检查是否有保存的winner
        const winnerId = genreWinners.get(genre.id);
        if (winnerId) {
          genre.winner = movies.find(m => m.id === winnerId);
        }
        
        return genre;
      })
      .sort((a, b) => b.movies.length - a.movies.length);
  }, [allTags, genreWinners]);

  // 只有一部电影的tag及其对应电影（用于在电影卡片上显示）
  const singleMovieTags = useMemo(() => {
    const singleTags = new Map<string, string[]>(); // movieId -> tags[]
    
    allTags.forEach((movies, tag) => {
      if (movies.length === 1) {
        const movieId = movies[0].id;
        if (!singleTags.has(movieId)) {
          singleTags.set(movieId, []);
        }
        singleTags.get(movieId)!.push(tag);
      }
    });
    
    return singleTags;
  }, [allTags]);

  // 注意：由于只有一部电影的tag不再显示在类型版图中，不再需要自动设置winner的逻辑

  // 处理电影双击
  const handleMovieDoubleClick = (movieId: string) => {
    const newSelected = new Set(selectedMovies);
    if (newSelected.has(movieId)) {
      newSelected.delete(movieId);
    } else {
      newSelected.add(movieId);
    }
    setSelectedMovies(newSelected);
  };

  // 计算统计数据
  const stats = useMemo(() => {
    const totalMovies = filteredMovies.length; // 总电影数，不是周数
    
    // 计算总观影时长（小时）
    // 如果有片长数据，使用实际片长；否则按每部2小时估算
    const totalMinutes = filteredMovies.reduce((sum, movie) => {
      if (movie.runtime && typeof movie.runtime === 'number' && movie.runtime > 0) {
        return sum + movie.runtime;
      }
      return sum + 120; // 默认2小时（120分钟）
    }, 0);
    const totalHours = Math.round(totalMinutes / 60);
    
    const topGenre = genres.length > 0 ? genres[0].tag : '暂无';
    return { totalMovies, totalHours, topGenre };
  }, [filteredMovies, genres]);

  return (
    <div className="min-h-screen bg-[#F0FDF4] text-slate-700 font-sans selection:bg-emerald-200 selection:text-emerald-900">
      {/* 顶部导航 */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur border-b border-green-100 px-4 py-3 flex justify-between items-center shadow-sm">
        {/* 左侧：标签切换和年份选择 */}
        <div className="flex items-center gap-3">
          <div className="flex gap-1 bg-green-100/50 p-1 rounded-full">
            {(['overview', 'calendar'] as const).map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition-all ${
                  activeTab === tab 
                    ? 'bg-white text-emerald-800 shadow text-emerald-700' 
                    : 'text-slate-500 hover:text-emerald-600'
                }`}
              >
                {tab === 'overview' && '年度总览'}
                {tab === 'calendar' && '周度记录'}
              </button>
            ))}
          </div>
          <div className="relative">
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              className="appearance-none bg-white border border-green-200 rounded-lg px-4 py-1.5 pr-8 text-sm font-medium text-emerald-800 hover:border-emerald-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 cursor-pointer"
            >
              <option value={2025}>2025</option>
              <option value={2024}>2024</option>
            </select>
            <ChevronDown className="absolute right-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-emerald-600 pointer-events-none" />
          </div>
        </div>
        
        {/* 右侧：更新按钮和电影数量 */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-600">已获取 {filteredMovies.length} 部电影</span>
          {activeTab === 'calendar' && (
            <button
              onClick={refreshFromDouban}
              disabled={loadingDouban}
              className="px-4 py-1.5 bg-emerald-600 text-white rounded-lg text-sm font-semibold hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              {loadingDouban ? '更新中...' : '从豆瓣更新'}
            </button>
          )}
          {activeTab === 'overview' && (
            <div className="flex items-center gap-3">
              <button
                onClick={refreshFromImdb}
                disabled={loadingImdb}
                className="px-4 py-1.5 bg-yellow-500 text-yellow-900 rounded-lg text-sm font-semibold hover:bg-yellow-600 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
              >
                {loadingImdb ? '更新中...' : '从IMDb更新'}
              </button>
              {updateProgress && (
                <div className="flex items-center gap-2 text-sm text-slate-600">
                  <div className="relative w-6 h-6">
                    <svg className="animate-spin h-6 w-6 text-emerald-500" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {updateProgress.total > 0 && (
                      <span className="absolute inset-0 flex items-center justify-center text-[10px] font-semibold text-emerald-600">
                        {updateProgress.percentage}%
                      </span>
                    )}
                  </div>
                  <span className="text-xs">{updateProgress.message}</span>
                  {updateProgress.total > 0 && (
                    <span className="text-slate-400 text-xs whitespace-nowrap">
                      {updateProgress.progress}/{updateProgress.total}
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </nav>

      <main className="max-w-full mx-auto px-24 py-8 pb-20">
        
        {/* 概览模式 */}
        {activeTab === 'overview' && (
          <div className="space-y-10 animate-fadeIn">
            {/* 核心数据卡片 */}
            <div className="grid grid-cols-3 gap-4">
              {[
                { label: '全年打卡', value: stats.totalMovies, icon: Film, unit: '部' },
                { label: '观影时长', value: stats.totalHours, icon: Clock, unit: 'h' },
                { label: '最爱类型', value: stats.topGenre, icon: Heart, unit: '' },
              ].map((item, idx) => (
                <div key={idx} className="bg-white border border-green-100 p-4 rounded-2xl flex flex-col items-center justify-center text-center hover:shadow-md hover:border-emerald-200 transition-all">
                  <item.icon className="w-6 h-6 text-emerald-500 mb-2 opacity-80" />
                  <div className="text-2xl font-bold text-slate-800">{item.value}<span className="text-xs text-slate-400 ml-1 font-normal">{item.unit}</span></div>
                  <div className="text-xs text-slate-400 mt-1">{item.label}</div>
                </div>
              ))}
            </div>

            {/* 饼状图 */}
            {pieChartData.length > 0 && (
              <div className="bg-white border border-green-100 rounded-xl p-6">
                <h3 className="text-xl font-bold mb-6 text-center text-emerald-900">You Say WHAT?</h3>
                <PieChart data={pieChartData} size={400} />
              </div>
            )}

            {/* 折线图 */}
            {lineChartData.length > 0 && (
              <div className="bg-white border border-green-100 rounded-xl p-6">
                <LineChart data={lineChartData} />
              </div>
            )}

            {/* 年度类型分布 */}
            {genres.length > 0 && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-bold flex items-center gap-2 text-emerald-900">
                    <Layers className="text-emerald-600" /> I Know <span className="font-bold">YOUR</span> Type
                  </h2>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  {genres.map((genre) => (
                    <div key={genre.id} className="bg-white border border-green-100 rounded-xl p-5 hover:border-emerald-300 hover:shadow-lg transition-all">
                      <div className="flex justify-between items-center mb-4">
                        <div className="flex items-center gap-3">
                          <Film className="w-5 h-5 text-emerald-600" />
                          <span className="font-bold text-lg text-slate-800">{genre.tag}</span>
                        </div>
                        <span className="text-2xl font-black text-slate-700">{genre.movies.length} <span className="text-sm font-normal text-slate-400">部</span></span>
                      </div>
                      
                      <div className="flex flex-wrap gap-2">
                        {genre.movies.map((movie) => {
                          const trophyKey = `${genre.id}-${movie.id}`;
                          const hasTrophy = trophyMovies.has(trophyKey);
                          return (
                            <span
                              key={movie.id}
                              onDoubleClick={() => {
                                const newTrophyMovies = new Set(trophyMovies);
                                if (hasTrophy) {
                                  newTrophyMovies.delete(trophyKey);
                                } else {
                                  newTrophyMovies.add(trophyKey);
                                }
                                setTrophyMovies(newTrophyMovies);
                              }}
                              className={`relative text-sm text-slate-600 bg-green-50/50 px-3 py-2 rounded border transition-all cursor-pointer ${
                                hasTrophy 
                                  ? 'ring-2 ring-yellow-400 border-yellow-300 hover:border-yellow-400 hover:text-emerald-800 hover:bg-white' 
                                  : 'border-green-100 hover:border-emerald-400 hover:text-emerald-800 hover:bg-white'
                              }`}
                            >
                              {movie.title}
                              {hasTrophy && (
                                <span className="absolute -top-2 -right-1 text-base leading-none">🏆</span>
                              )}
                            </span>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

          </div>
        )}

        {/* 周度记录模式 */}
        {activeTab === 'calendar' && (
          <div className="animate-fadeIn">
            {loading ? (
              <div className="text-center py-12 text-slate-400">加载中...</div>
            ) : weeklyLog.length === 0 ? (
              <div className="text-center py-12 text-slate-400">暂无数据</div>
            ) : (
              <div className="grid grid-cols-7 gap-6">
                {weeklyLog.flatMap((log) =>
                  log.movies.map((movie) => {
                    const isFiveStar = movie.rating === 5;
                    const isSelected = selectedMovies.has(movie.id);
                    const isPoleToWin = isFiveStar && isSelected;
                    const date = new Date(movie.date);
                    const dayIdx = date.getDay() === 0 ? 6 : date.getDay() - 1;
                    const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];
                    
                    return (
                      <div
                        key={movie.id}
                        onDoubleClick={() => handleMovieDoubleClick(movie.id)}
                        className={`relative rounded-xl overflow-hidden cursor-pointer transition-all transform hover:scale-105 aspect-[2/3] ${
                          isFiveStar ? 'ring-4 ring-green-500 shadow-2xl shadow-green-500/50' : ''
                        } ${isSelected ? 'ring-4 ring-yellow-400 shadow-2xl shadow-yellow-400/50' : ''}`}
                      >
                        {movie.id ? (
                          <div className="relative w-full h-full">
                            <img
                              src={`${API_BASE_URL}/api/posters/${movie.id}.jpg`}
                              alt={movie.title}
                              className="w-full h-full object-cover"
                              loading="lazy"
                              onError={(e) => {
                                // 如果本地poster加载失败，显示占位符
                                const target = e.target as HTMLImageElement;
                                const parent = target.parentElement;
                                if (parent && !parent.querySelector('.poster-placeholder')) {
                                  target.style.display = 'none';
                                  const placeholder = document.createElement('div');
                                  placeholder.className = 'poster-placeholder w-full h-full bg-gradient-to-br from-emerald-100 to-green-200 flex flex-col items-center justify-center text-slate-600 p-4';
                                  placeholder.innerHTML = `
                                    <div class="text-4xl mb-2">🎬</div>
                                    <div class="text-sm font-semibold text-center">${movie.title}</div>
                                  `;
                                  parent.appendChild(placeholder);
                                }
                              }}
                            />
                            {isPoleToWin && (
                              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-400 text-yellow-900 text-xs font-bold py-2 px-4 text-center z-20 shadow-xl whitespace-nowrap">
                                🏁 POLE-TO-WIN 🏁
                              </div>
                            )}
                            <div className="absolute top-2 left-2 text-[10px] px-2 py-1 rounded-full bg-emerald-600 text-white shadow-lg font-semibold">
                              Week {log.week}
                            </div>
                            <div className="absolute top-2 right-2 text-[10px] px-2 py-1 rounded-full bg-white/80 text-emerald-700 border border-emerald-100 font-medium">
                              {new Date(log.date).toLocaleDateString('zh-CN', {
                                month: 'short',
                                day: 'numeric',
                              })}
                            </div>
                            {singleMovieTags.has(movie.id) && (
                              <div className="absolute top-12 right-2 flex flex-col gap-1 z-10">
                                {singleMovieTags.get(movie.id)!.map((tag, idx) => (
                                  <span key={idx} className="bg-emerald-500/80 text-white text-[9px] font-medium px-2 py-1 rounded text-center">
                                    {tag}
                                  </span>
                                ))}
                              </div>
                            )}
                            {isSelected && !isPoleToWin && (
                              <div className="absolute bottom-2 right-2 bg-yellow-400 rounded-full p-1.5 shadow-lg z-10">
                                <Trophy size={16} className="text-yellow-900" fill="currentColor" />
                              </div>
                            )}
                            <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/90 via-black/70 to-transparent p-3">
                              <div className="text-white text-sm font-bold truncate mb-1">{movie.title}</div>
                              <div className="text-emerald-300 text-xs mb-1">
                                {movie.rating ? '⭐'.repeat(movie.rating) : '未评分'}
                              </div>
                              <div className="flex gap-1 text-slate-300 text-[10px]">
                                {weekDays.map((day, idx) => (
                                  <span
                                    key={idx}
                                    className={idx === dayIdx ? 'text-emerald-400 font-bold' : ''}
                                  >
                                    {day}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ) : (
                          <div className="w-full h-full bg-slate-200 flex flex-col items-center justify-center text-slate-600 text-sm p-2 text-center">
                            <div className="font-semibold mb-1">{movie.title}</div>
                            <div className="text-xs">
                              {movie.rating ? '⭐'.repeat(movie.rating) : '未评分'}
                            </div>
                            <div className="flex gap-1 text-xs mt-1">
                              {weekDays.map((day, idx) => (
                                <span
                                  key={idx}
                                  className={idx === dayIdx ? 'text-emerald-600 font-bold' : ''}
                                >
                                  {day}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
};

// 辅助函数：计算周数
function getWeekNumber(date: Date): number {
  const d = new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()));
  const dayNum = d.getUTCDay() || 7;
  d.setUTCDate(d.getUTCDate() + 4 - dayNum);
  const yearStart = new Date(Date.UTC(d.getUTCFullYear(), 0, 1));
  return Math.ceil((((d.getTime() - yearStart.getTime()) / 86400000) + 1) / 7);
}

export default MovieRewindApp;
