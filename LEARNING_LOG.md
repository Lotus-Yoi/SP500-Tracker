# SP500-Tracker Learning Log

> 这不是项目文档，而是项目背后的学习轨迹：记录学会了什么、踩过什么坑、哪些概念还会反复忘，以及哪些东西已经逐渐变成直觉。

## 已经形成的核心理解

### 数据与 Pandas
- 能区分 DataFrame、Series 和 Index，并知道把日期设为 DatetimeIndex 后可以按日期对齐和切片。
- 理解 `pd.to_datetime()`、`pd.to_numeric(..., errors="coerce")`、`dropna(subset=...)` 的职责。
- 理解原始字段和派生字段不同：SP500 是原始数据，`daily_return` 是计算出来的派生数据。
- 理解 `pct_change()` 第一行出现 NaN 是数学上正常的，因为没有上一条数据可比较。
- 理解数据处理应先建立可靠的数据状态，再进行收益率等派生分析。
- 理解不同数据源横向合并时，可以保留有意义的 NaN，而不是看到 NaN 就整行删除。

### 循环与数据结构
- 循环本身不会自动保存每一轮结果；如果后续还需要结果，就要主动存入 list 或 dict。
- list 适合保存“很多个同类对象”，dict 适合用 key 给对象建立明确映射。
- 在 V1.3 中用 `market_data[series_id] = df` 保存四个 FRED 指标，避免循环结束后只剩最后一个 df。
- 新闻处理中，`all_news` 保存多页原始新闻，`clean_news` 保存筛选字段后的新闻。
- 一篇新闻是 dict，多篇新闻组成 list。

### API 与 requests
- 理解 GET / POST 的基本请求流程。
- Response 对象不只是响应正文：
  - `.text`：文本正文
  - `.json()`：解析 JSON
  - `.status_code`：HTTP 状态码
  - `.raise_for_status()`：遇到 HTTP 错误时抛异常
- 理解 Marketaux 的 `params` 是查询参数。
- 初步理解 DeepSeek 请求中的 headers 和 body：
  - headers：认证、内容类型等请求信息
  - body：模型、messages、prompt 等真正发送的数据
- 理解 JSON 解析后会变成 Python 的 dict / list / str / number 等数据结构。
- 能通过 `data["choices"][0]["message"]["content"]` 理解“dict 按 key，list 按下标”逐层取值。

### Git / GitHub / Actions
- 理解 working tree → staging → commit → push → GitHub 的基本流程。
- 理解 commit 是历史记录，push 是上传，tag 是给稳定版本命名。
- 理解 GitHub Actions 可以在云端 Linux 环境定时运行项目，即使本机关闭。
- 理解 exit code 0 表示成功，非 0（例如 1）表示失败，对 CI 很重要。
- 已经经历过 GitHub Actions bot 修改仓库后，本地 push 被拒绝，需要先 pull 的情况。

## 项目中踩过的重要坑

### 1. dropna 导致历史数据不断缩水
曾经直接对包含 `daily_return` 的 DataFrame 使用 `dropna()`。

由于 `pct_change()` 第一行必然是 NaN，每次运行都会删除第一条有效 SP500 价格；重新计算收益率后新的第一行再次变成 NaN，于是历史数据每运行一次少一行。

修正思路：
- 清洗时只针对原始必要字段，例如 SP500 和 observation_date。
- 不因为派生字段的正常 NaN 删除原始数据。

### 2. 新数据可能用 NaN 覆盖旧的有效数据
如果先 concat、同日期保留新数据，再清洗，新下载的同日期 NaN 可能覆盖本地有效价格。

修正思路：
- old/new 数据先分别清洗。
- 再合并、去重、排序。

### 3. 首次运行和更新运行走了不同的数据状态
早期版本在“没有本地 CSV”时跳过了 merge_data，导致首次运行可能没有去重和排序。

形成的原则：
> 无论程序从哪个分支进入，在进行派生计算前，都应该先到达同一个定义明确的数据状态。

### 4. 循环结果被覆盖
曾经在循环中反复给同一个 `df/new_df` 赋值，循环结束后只剩最后一个指标。

修正：
- 需要保留每轮结果时，用 list / dict 主动保存。

### 5. 字符串和变量混淆
曾写过：
```python
"published_after": "time_string"
"content": "news_prompt"
```

这发送的是字面字符串，而不是变量保存的值。

形成的判断：
- 想要变量里的值 → 不加引号。
- 想要这些文字本身 → 加引号。

### 6. requests.post 的位置参数导致 401
曾写：
```python
requests.post(url, headers, json=body, timeout=60)
```

变量叫 `headers` 并不会让 Python 自动把它传给函数的 headers 参数；不写参数名时按位置传递，导致认证头没有正确发送。

修正：
```python
requests.post(url, headers=headers, json=body, timeout=60)
```

由此真正理解：
- positional argument：位置参数
- keyword argument：关键字参数

### 7. API 超时
DeepSeek 在输入真实市场数据和多篇新闻后，10 秒 timeout 不够，出现 ReadTimeout。

修正：
- 将超时时间提高到 60 秒。
- 网络请求增加有限次数重试。

### 8. 异常信息被吃掉
只打印“请求失败”很难调试。

后来使用：
```python
except requests.exceptions.RequestException as e:
```
打印 `e`，可以看到 ReadTimeout、401、ConnectionError 等具体原因。

## V1.3 新增的数据流理解

### 市场线
```text
FRED
→ SP500 / VIXCLS / DGS10 / DCOILWTICO
→ 每个指标 fetch + clean
→ market_data 字典
→ 四个 DataFrame 按日期索引横向合并（axis=1）
→ for_AI_df
→ tail(7)
→ to_string()
→ market_text
```

四个指标：
- SP500：S&P 500 指数
- VIXCLS：VIX，市场预期波动率
- DGS10：美国 10 年期国债收益率
- DCOILWTICO：WTI 原油价格

不同指标日期不完全一致时保留 NaN，因为“该来源当天没有观测”本身不意味着其他来源当天的数据无效。

### 新闻线
```text
Marketaux
→ 最近 24 小时 + 搜索条件
→ 分页请求前三页
→ data["data"]
→ all_news
→ 只保留 title / snippet / source / published_at
→ clean_news
→ f-string + +=
→ news_text
```

Python 负责机械筛选（时间、搜索词、字段）；LLM 负责语义判断哪些候选新闻真正与整体市场有关。

### LLM 汇合
```text
market_text ─┐
             ├→ news_prompt → DeepSeek API → response → report → report.txt
news_text ───┘
```

Prompt 特别要求：
- 区分已知事实和可能的市场驱动因素。
- 不把相关性直接写成确定因果。
- 信息不足时明确说不足，不编造原因。

## 目前仍容易忘 / 需要继续练

- `axis=0` 与 `axis=1` 容易混：
  - axis=0：上下拼
  - axis=1：左右拼
- `DataFrame.to_string()` 方法名容易忘。
- VIX 的具体含义容易忘：它是市场预期波动率，不等于“股市会跌”。
- `fetch_fred_data()` 返回 Response，而不是直接返回 DataFrame；Response 还要经过 `.text → StringIO → pd.read_csv()`。
- `combine_market_data()` 接收的是保存四个 DataFrame 的字典，而不是两个 df。
- DeepSeek body 中 `messages / role / content` 的具体结构还不熟，需要使用几次后形成记忆。
- 位置参数与关键字参数刚刚建立理解，需要继续在真实代码中使用。
- `all_news` 与 `clean_news` 的职责已经能回忆，但分页、清洗、拼字符串的具体代码还没有形成肌肉记忆。

## 已经从“容易忘”开始变稳定的东西

- 循环结果需要后续使用时必须主动保存。
- list 与 dict 的基本职责。
- 字符串字面量和变量值的区别。
- 网络请求应该有超时、异常处理和有限重试。
- 第一行 `daily_return = NaN` 是正常现象，不能因此删除有效价格。
- 数据先清洗/合并成可靠状态，再做分析。

---

这份文件会随着项目继续更新。目标不是记录所有语法，而是记录真正改变了理解方式的知识、错误和工程经验。
