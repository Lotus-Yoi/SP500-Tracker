import requests
import os
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO

url='https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500'
response = None
for i in range(3):
    try:
       response = requests.get(url,timeout=10)
       response.raise_for_status()
       break                
    except requests.exceptions.RequestException:
        response = None
        print(f"第{i+1}次获取失败")
if response is None:
    print("连续三次请求失败，程序结束")
    raise SystemExit

if os.path.exists("sp500.csv"):
    print("已检测到本地数据，执行更新")
else:
    with open("sp500.csv","w") as f:
        f.write(response.text)
    print("没有本地文件，创建原始数据")

df=pd.read_csv("sp500.csv")
df['observation_date']=pd.to_datetime(df["observation_date"])
df=df.dropna()
df=df.set_index("observation_date")
df["daily_return"]=df["SP500"].pct_change()*100

last_date=df.index.max()
new_df=pd.read_csv(StringIO(response.text))
new_df["observation_date"]=pd.to_datetime(new_df["observation_date"])
new_df=new_df.dropna()
new_df=new_df.set_index("observation_date")
new_df["daily_return"]=new_df["SP500"].pct_change()*100

new_df=new_df[new_df.index > last_date]
test_df=pd.concat([df,new_df])
test_df=test_df.sort_index()
test_df.to_csv("sp500.csv")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

plt.subplot(2,1,1)
plt.plot(test_df.index, test_df["SP500"])
plt.ylabel("价格")
plt.title("SP500价格变化趋势")

plt.subplot(2,1,2)
plt.plot(test_df.index, test_df["daily_return"])
plt.ylabel("涨幅")
plt.title("SP500的涨跌趋势")

plt.tight_layout()
plt.savefig("SP500.png")
plt.show()

