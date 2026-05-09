import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

# 初始化 Supabase 客户端
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(supabase_url, supabase_key)

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

def classify_news(title, content):
    """调用 DeepSeek API 对单条新闻进行分类、打分、摘要"""
    
    # 构建要发给大模型的提示词
    prompt = f"""你是一个AI行业信息分类助手。
下面是一条AI相关的新闻，请完成三件事：
1. 分类：从[模型发布、产品发布、行业动态、论文研究、技巧观点]中选一个最合适的
2. 打分：1-10分，判断这条信息的重要程度（10分最重要）
3. 摘要：用一句中文概括核心内容，不超过50字

新闻标题：{title}
新闻内容：{content}

请严格按照以下JSON格式返回，不要返回其他内容：
{{"category": "分类", "score": 数字, "summary": "摘要"}}"""

    # 发送请求给 DeepSeek
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,  # 降低随机性，让输出更稳定
        "max_tokens": 200
    }
    
    try:
        response = requests.post(DEEPSEEK_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # 提取大模型返回的文本
            ai_response = result["choices"][0]["message"]["content"]
            
            # 尝试解析 JSON
            import json
            # 处理可能的 JSON 格式问题（去掉多余的反引号）
            ai_response = ai_response.strip()
            if ai_response.startswith("```json"):
                ai_response = ai_response[7:]
            if ai_response.startswith("```"):
                ai_response = ai_response[3:]
            if ai_response.endswith("```"):
                ai_response = ai_response[:-3]
            
            parsed = json.loads(ai_response.strip())
            return parsed["category"], parsed["score"], parsed["summary"]
        else:
            print(f"  API 请求失败: {response.status_code} - {response.text}")
            return None, None, None
            
    except Exception as e:
        print(f"  处理失败: {e}")
        return None, None, None

def process_unprocessed_news():
    """处理所有未分类的新闻"""
    
    # 从数据库读取 category 为空的新闻（还没处理过的）
    response = supabase.table('news').select('id, title, raw_content').is_('category', 'null').execute()
    
    news_list = response.data
    total = len(news_list)
    
    print(f"找到 {total} 条未处理的新闻")
    
    if total == 0:
        print("没有需要处理的新闻")
        return
    
    for i, news in enumerate(news_list):
        news_id = news['id']
        title = news['title']
        content = news.get('raw_content', '')
        
        # 如果内容为空，用标题代替
        if not content:
            content = title
        
        print(f"[{i+1}/{total}] 处理: {title[:40]}...")
        
        # 调用大模型分类
        category, score, summary = classify_news(title, content)
        
        if category and score and summary:
            # 更新数据库
            supabase.table('news').update({
                'category': category,
                'score': score,
                'summary': summary
            }).eq('id', news_id).execute()
            print(f"  ✅ 分类: {category} | 评分: {score} | 摘要: {summary[:30]}...")
        else:
            print(f"  ❌ 处理失败，跳过")
        
        # 避免请求太快，加一个小延迟
        import time
        time.sleep(0.5)
    
    print("\n处理完成！")

if __name__ == "__main__":
    process_unprocessed_news()