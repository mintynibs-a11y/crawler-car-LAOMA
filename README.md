# 汽车外饰设计评论爬虫

收集**小红书**、**京东**、**Bilibili**、**知乎**上关于汽车外饰设计的用户评论/评价。

---

## 项目结构

```
crawler-car-LAOMA/
├── main.py                   # CLI 入口
├── requirements.txt
├── output/                   # 爬取结果默认输出目录
├── src/
│   ├── models.py             # Comment / CrawlResult 数据模型
│   ├── utils.py              # 请求工具、限速、保存文件
│   └── crawlers/
│       ├── base.py           # 抽象基类
│       ├── bilibili.py       # Bilibili 爬虫
│       ├── jd.py             # 京东爬虫
│       ├── xiaohongshu.py    # 小红书爬虫
│       └── zhihu.py          # 知乎爬虫
└── tests/
    ├── test_models.py
    ├── test_crawlers.py
    └── test_utils.py
```

---

## 安装依赖

```bash
pip install -r requirements.txt
```

---

## 快速开始

```bash
# 爬取所有平台，使用默认关键词（汽车外饰、车身改色膜……）
python main.py

# 自定义关键词
python main.py --keyword "汽车外饰改装" "车身贴膜"

# 仅爬取部分平台
python main.py --platforms jd bilibili

# 限制每个关键词爬取页数
python main.py --max-pages 3

# 以 CSV 格式输出
python main.py --format csv

# 同时输出 JSON 和 CSV
python main.py --format both

# 指定输出目录
python main.py --output-dir ./data
```

---

## 平台说明

### 小红书 (Xiaohongshu)

小红书接口需要登录态 Cookie。请在浏览器登录小红书后，从开发者工具中复制完整
的 `Cookie` 请求头，并通过环境变量传入：

```bash
export XHS_COOKIE="<your cookie string here>"
python main.py --platforms xiaohongshu
```

### 京东 (JD.com)

通过关键词搜索商品，再拉取商品评价。无需登录，可直接使用。

### Bilibili

使用 Bilibili 公开搜索和评论接口，无需登录。

### 知乎 (Zhihu)

使用知乎搜索问题、获取回答内容（以回答作为评论单元）。

---

## 输出格式

每次运行在 `output/` 目录下生成：

| 文件 | 内容 |
|------|------|
| `<平台>_<关键词>_<时间戳>.json` | 单平台单关键词评论 |
| `all_comments_<时间戳>.json` | 所有平台合并评论 |
| `summary_<时间戳>.json` | 爬取摘要（各平台条数、成功状态） |

每条评论包含以下字段：

```json
{
  "platform": "京东",
  "comment_id": "123456",
  "content": "外饰设计很漂亮，做工精细",
  "author": "买家昵称",
  "author_id": "uid",
  "publish_time": "2024-01-15 10:00:00",
  "likes": 10,
  "replies": 2,
  "source_url": "https://item.jd.com/xxx.html",
  "source_title": "商品标题",
  "keyword": "汽车外饰",
  "extra": {},
  "crawled_at": "2024-03-14T12:00:00"
}
```

---

## 运行测试

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## 注意事项

- 本工具仅用于**学习和研究目的**，请遵守各平台使用条款。
- 爬取间隔已内置随机延迟（1–3 秒），请勿大幅减少以避免触发封禁。
- 小红书接口有签名校验，需要提供有效 Cookie 才能正常使用。
