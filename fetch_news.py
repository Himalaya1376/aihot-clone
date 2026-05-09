import feedparser
import os
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Supabase 客户端
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# 定义要抓取的 RSS 源
RSS_SOURCES = [
    {
        "name": "OpenAI",
        "url": "https://openai.com/blog/rss.xml"
    },
    {
        "name": "Hugging Face",
        "url": "https://huggingface.co/blog/feed.xml"
    }
]

def fetch_and_save():
    """抓取所有 RSS 源并存入数据库"""
    
    for source in RSS_SOURCES:
        print(f"正在抓取: {source['name']} - {source['url']}")
        
        try:
            # 使用 feedparser 解析 RSS
            feed = feedparser.parse(source['url'])
            
            # 遍历每一条新闻
            for entry in feed.entries:
                # 提取标题
                title = entry.get('title', '')
                # 提取链接
                url = entry.get('link', '')
                # 提取发布时间
                published_at = entry.get('published_parsed')
                if published_at:
                    published_at = datetime(*published_at[:6])
                # 提取摘要
                summary = entry.get('summary', '')
                
                # 准备要存入数据库的数据
                news_item = {
                    "title": title,
                    "url": url,
                    "source": source['name'],
                    "published_at": published_at.isoformat() if published_at else None,
                    "raw_content": summary,
                    "category": None,
                    "score": None,
                    "summary": None
                }
                
                # 存入 Supabase（如果 url 已存在则跳过）
                result = supabase.table('news').upsert(news_item, on_conflict='url').execute()
                
                print(f"  ✅ 已存入: {title[:50]}...")
                
        except Exception as e:
            print(f"  ❌ 抓取失败: {e}")
    
    print("\n抓取完成！")

if __name__ == "__main__":
    fetch_and_save()