"""每日热点数据源 — 知乎热榜 + 百度热搜"""
import json
import urllib.request
import urllib.error
import time
from typing import List, Dict

# ── 知乎 ──
ZHIHU_URL = "https://api.zhihu.com/topstory/hot-list"
ZHIHU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.zhihu.com/hot",
}


def fetch_zhihu_hot(limit: int = 20) -> List[Dict]:
    """获取知乎热榜，返回统一格式"""
    url = f"{ZHIHU_URL}?limit={limit}"
    req = urllib.request.Request(url, headers=ZHIHU_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"[知乎] 请求失败: {e}")
        return []

    items = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")
    for rank, item in enumerate(data.get("data", [])[:limit], 1):
        target = item.get("target", {}) if isinstance(item.get("target"), dict) else item
        title = target.get("title", "")
        if not title:
            continue

        raw_url = target.get("url", "")
        question_url = raw_url.replace("api", "www").replace("questions", "question") if raw_url else ""

        # 热度解析
        detail = item.get("detail_text", "")
        heat = _parse_zhihu_heat(detail)

        items.append({
            "rank": rank,
            "title": title,
            "url": question_url,
            "heat": heat,
            "source": "知乎",
            "extra": f"{target.get('answer_count', 0) or 0} 回答",
            "scraped_at": now,
        })
    return items


def _parse_zhihu_heat(detail_text: str) -> str:
    """将 '123 万热度' → '123 万'"""
    if not detail_text:
        return ""
    import re
    m = re.search(r'([\d.]+)\s*万', str(detail_text))
    return f"{m.group(1)} 万" if m else str(detail_text).strip()


# ── 百度 ──
BAIDU_URL = "https://top.baidu.com/board?tab=realtime"
BAIDU_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )
}


def fetch_baidu_hot(limit: int = 20) -> List[Dict]:
    """获取百度热搜，使用 BeautifulSoup 解析"""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("[百度] BeautifulSoup 未安装，跳过")
        return []

    req = urllib.request.Request(BAIDU_URL, headers=BAIDU_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[百度] 请求失败: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    items = []
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    cards = soup.find_all("div", class_="category-wrap_iQLoo")
    for i, card in enumerate(cards[:limit], 1):
        # 标题
        title_div = card.find("div", class_="c-single-text-ellipsis")
        title = title_div.get_text(strip=True) if title_div else ""
        if not title:
            continue

        # 热度
        hot_div = card.find("div", class_="hot-index_1Bl1a")
        heat = hot_div.get_text(strip=True) if hot_div else ""

        # 描述
        desc_div = card.find("div", class_="hot-desc_1m_jR")
        desc = desc_div.get_text(strip=True).replace("查看更多>", "").strip() if desc_div else ""

        # 链接
        link_tag = card.find("a", href=True)
        url = link_tag["href"] if link_tag else ""
        if url and not url.startswith("http"):
            url = "https://www.baidu.com" + url

        items.append({
            "rank": i,
            "title": title,
            "url": url,
            "heat": heat,
            "source": "百度",
            "extra": desc,
            "scraped_at": now,
        })
    return items


# ── 统一入口 ──
def fetch_all_hot(limit: int = 20) -> List[Dict]:
    """获取所有平台热点，合并后按来源分组返回"""
    all_items = []
    all_items.extend(fetch_zhihu_hot(limit))
    all_items.extend(fetch_baidu_hot(limit))
    return all_items
