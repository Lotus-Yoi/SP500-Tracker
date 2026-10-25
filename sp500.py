import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta,timezone
import sys
import os
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv()

def fetch_fred_data(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    response=None
    for i in range(3):
        try:
            response=requests.get(url,timeout=10)
            response.raise_for_status()
            break

        except requests.exceptions.RequestException:
            response=None
            print(f"fred第{i+1}次获取失败")

    if response is None:
        raise SystemExit(1)

    return response

def fetch_news():
    sys.stdout.reconfigure(encoding="utf-8")

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(hours= 24)
    time_string = yesterday.strftime("%Y-%m-%dT%H:%M")

    url = "https://api.marketaux.com/v1/news/all"
    api_key = os.getenv("Marketaux_API_KEY")
    params = {
        "api_token":api_key,
            "language":"en",
            "published_after":time_string,
            "countries": "us",
            "search": "S&P 500"
    }

    all_news=[]
    response = None

    for page in range(1,4):
        params["page"] = page
        for i in range(3):
            try:
                response = requests.get(url,params=params,timeout=10)
                response.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                response = None
                status = e.response.status_code if e.response is not None else "无 HTTP 响应"
                print(f"Marketaux第{i+1}次请求出错：{type(e).__name__}，状态码：{status}")
        if response is None:
            raise SystemExit(1)
        data = response.json()
        news_list = data["data"]
        for news in news_list:
            all_news.append(news)

    clean_news = []

    for news in all_news:
        new_news = {
            "title":news["title"],
            "snippet":news["snippet"],
            "source":news["source"],
            "published_at":news["published_at"]
            }
        clean_news.append(new_news)
    return clean_news

def generate_report(market_text,news_text):
    api_key = os.getenv("DEEPSEEK_API_KEY")

    url = "https://api.deepseek.com/chat/completions"
    news_prompt = f"""
    你是一名金融市场分析助手。

你的任务不是生成模板，也不是告诉我如何分析。
请直接根据下面提供的市场数据和候选新闻，生成今天的 S&P 500 市场分析报告。

【市场数据】
{market_text}

【候选新闻】
{news_text}

要求：
1. 先说明 S&P 500 最近的实际走势。
2. 从候选新闻中筛选真正可能影响美国整体市场的事件。
3. 结合 VIX、10年期美债收益率和 WTI 原油价格提供背景。
4. 区分“已知事实”和“可能的市场驱动因素”，不要把相关性写成确定因果关系。
5. 忽略广告、Cookie、订阅提示以及明显无关的个股内容。
6. 如果现有材料不足以解释市场波动，明确写“现有信息不足以确定主要原因”，不要编造。
7. 直接输出中文市场报告，不要输出提示词、模板或写作建议。
"""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    body = {
        "model": "deepseek-flash",
        "messages": [
            {
                "role": "user",
                "content": news_prompt
            }
        ]
    }
    response = None
    for i in range(3):
        try:
            response = requests.post(
                url,
                headers=headers,
                json=body,
                timeout=60
            )
            response.raise_for_status()
            break

        except requests.exceptions.RequestException as e:
            response = None
            print(f"deepseek第{i+1}次请求出错:{e}")

    if response is None:
        raise SystemExit(1)
    
    data = response.json()
    report = data["choices"][0]["message"]["content"]

    return report


def clean_data(df):
    series_name=df.columns[1]
    df["observation_date"]=pd.to_datetime(df["observation_date"])
    df[series_name]=pd.to_numeric(df[series_name],errors="coerce")

    df=df.dropna(subset=[series_name,"observation_date"])
    df=df.set_index("observation_date")

    df = df[~df.index.duplicated(keep="last")]
    df = df.sort_index()

    if df.empty:
        raise ValueError("清洗后无有效数据")

    return df

def combine_market_data(market_data):
    df=pd.concat(
        market_data.values(),
        axis=1,
        join="outer",
        sort=True
        )
    return df

def main():
    series_ids=["SP500","VIXCLS","DGS10","DCOILWTICO"]
    market_data={}
    for series_id in series_ids:

        response=fetch_fred_data(series_id)

        for_AI_df=pd.read_csv(StringIO(response.text))

        for_AI_df=clean_data(for_AI_df)

        market_data[series_id] = for_AI_df

    new_df=market_data["SP500"]
    new_df["daily_return"]=new_df["SP500"].pct_change()*100

    for_AI_df=combine_market_data(market_data)

    recent_market = for_AI_df.tail(7)
    market_text = recent_market.to_string()

    clean_news =fetch_news()

    news_text=""

    for news in clean_news:
        news_text += f"Title:{news['title']}\n"
        news_text += f"Snippet:{news['snippet']}\n"
        news_text += f"Source:{news['source']}\n"
        news_text += f"published_at:{news['published_at']}\n"
        news_text += "------------------------------\n"

    report = generate_report(market_text, news_text)
    
    today = datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d")

    report_dir = Path("reports")
    report_dir.mkdir(exist_ok=True)

    report_path = report_dir / f"{today}.txt"

    with open(report_path,"w",encoding="utf-8") as f:
        f.write(report)

if __name__ == "__main__":
    main()


