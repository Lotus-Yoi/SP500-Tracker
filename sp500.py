import pandas as pd
import requests
import os
from io import StringIO
import matplotlib.pyplot as plt

def fetch_data(url):
    response=None
    for i in range(3):
        try:
            response=requests.get(url,timeout=10)
            response.raise_for_status()
            break
        except requests.exceptions.RequestException:
            response=None
            print(f"第{i+1}次获取失败")
    if response is None:
        print("连续三次请求失败，程序结束")
        raise SystemExit(1)
    return response

def clean_data(df):
    df['observation_date']=pd.to_datetime(df['observation_date'])
    df['SP500']=pd.to_numeric(df['SP500'],errors="coerce")
    df = df.dropna(subset=["SP500"])
    df=df.set_index('observation_date')
    return df

# new_df=pd.read_csv(StringIO(response.text))
# new_df['observation_date']=pd.to_datetime(new_df['observation_date'])
# new_df['SP500']=pd.to_numeric(new_df['SP500'],errors="coerce")
# new_df = new_df.dropna(subset=["SP500"])
# new_df=new_df.set_index('observation_date')

# last_date=max(df['observation_date'])
# new_df=new_df[new_df['observation_date']>last_date]设置成index以后就不在new_df['observation_date']里面了
# new_df=new_df[new_df.index>max(df.index)]这句可以删掉了，万一本地有错误，只拿新日期的就没法修改旧的错误了


def merge_data(old_data,new_data):
    combined_df=pd.concat([old_data,new_data])
    combined_df=combined_df[~combined_df.index.duplicated(keep='last')]
    combined_df = combined_df.sort_index()
    # 永远不要假设去重、拼接后的数据顺序还是对的
    combined_df['daily_return']=combined_df['SP500'].pct_change()*100
    return combined_df

def paint(df):
    plt.subplot(2,1,1)
    plt.plot(df.index,df["SP500"])
   
    plt.ylabel("Price")
    plt.title("S&P 500 Price Trend")

    plt.subplot(2,1,2)
    plt.plot(df.index,df["daily_return"])

    plt.ylabel("Daily Return(%)")
    plt.title("S&P 500 Daily Return")

    plt.tight_layout()
    plt.savefig("SP500.png")
    plt.close()

def main():
    url='https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500'
    response=fetch_data(url)

    new_df=pd.read_csv(StringIO(response.text))
    new_df=clean_data(new_df)

    if os.path.exists("sp500.csv"):
        print("检测到已有数据，正在更新")

        old_df=pd.read_csv("sp500.csv")
        old_df=clean_data(old_df)

        combined_df=merge_data(old_df,new_df)

    else:
        # with open("sp500.csv","w") as f:
        #     f.write(response.text)
        print("未检测到数据，正在创建原始数据")
        combined_df=new_df
    combined_df.to_csv("sp500.csv")
# to_csv会创建csv文件
    paint(combined_df)
if __name__ == "__main__":
    main()




    




