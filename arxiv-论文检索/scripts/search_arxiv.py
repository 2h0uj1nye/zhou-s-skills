#!/usr/bin/env python3
"""Search arXiv and display results in a clean format.

Usage:
    python3 search_arxiv.py "GRPO reinforcement learning"
    python3 search_arxiv.py "GRPO reinforcement learning" --max 10
    python3 search_arxiv.py "GRPO reinforcement learning" --sort date
    python3 search_arxiv.py --author "Yann LeCun" --max 5
    python3 search_arxiv.py --category cs.AI --sort date --max 10
    python3 search_arxiv.py --id 2402.03300
    python3 search_arxiv.py --id 2402.03300,2401.12345

注意：arXiv 会对密集请求间歇性返回 406/429/503，本脚本内置重试与退避；
连续失败时打印可读原因并返回非零码，不吐 traceback。
"""
import random
import sys
import time
import urllib.request
import urllib.error
import urllib.parse
import xml.etree.ElementTree as ET

NS = {'a': 'http://www.w3.org/2005/Atom'}

# arXiv 建议使用能表明身份与用途的 UA；同时避免被当成未知爬虫
USER_AGENT = 'arxiv-search-skill/1.0 (local research helper; python-urllib)'
RETRYABLE_STATUS = {406, 429, 500, 502, 503, 504}
MAX_ATTEMPTS = 5
BACKOFF_SECONDS = 3.0
# arXiv 的限流会持续数十秒（表现为 406），退避要给足并加抖动
BACKOFF_FACTOR = 2.0
BACKOFF_JITTER = 1.5


def fetch(url, timeout=20):
    """带重试与退避的 GET，返回 bytes；失败时抛出带可读信息的 RuntimeError。"""
    last = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as exc:
            last = f'HTTP {exc.code} {exc.reason}'
            if exc.code not in RETRYABLE_STATUS:
                break
        except urllib.error.URLError as exc:
            last = f'网络错误：{exc.reason}'
        except TimeoutError:
            last = '请求超时'
        if attempt < MAX_ATTEMPTS:
            delay = BACKOFF_SECONDS * (BACKOFF_FACTOR ** (attempt - 1)) + random.uniform(0, BACKOFF_JITTER)
            print(f'[重试 {attempt}/{MAX_ATTEMPTS - 1}] {last}，{delay:.0f}s 后重试…', file=sys.stderr)
            time.sleep(delay)
    raise RuntimeError(last or '未知错误')


# --- 参数拼装 ---
def search(query=None, author=None, category=None, ids=None, max_results=5, sort="relevance"):
    params = {}
    
    if ids:
        params['id_list'] = ids
    else:
        parts = []
        if query:
            parts.append(f'all:{urllib.parse.quote(query)}')
        if author:
            parts.append(f'au:{urllib.parse.quote(author)}')
        if category:
            parts.append(f'cat:{category}')
        if not parts:
            print("Error: provide a query, --author, --category, or --id")
            sys.exit(1)
        params['search_query'] = '+AND+'.join(parts)
    
    params['max_results'] = str(max_results)
    
    sort_map = {"relevance": "relevance", "date": "submittedDate", "updated": "lastUpdatedDate"}
    params['sortBy'] = sort_map.get(sort, sort)
    params['sortOrder'] = 'descending'
    
    url = "https://export.arxiv.org/api/query?" + "&".join(f"{k}={v}" for k, v in params.items())
    
    data = fetch(url)
    
    root = ET.fromstring(data)
    entries = root.findall('a:entry', NS)
    
    if not entries:
        print("No results found.")
        return
    
    total = root.find('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
    if total is not None:
        print(f"Found {total.text} results (showing {len(entries)})\n")
    
    for i, entry in enumerate(entries):
        title = entry.find('a:title', NS).text.strip().replace('\n', ' ')
        raw_id = entry.find('a:id', NS).text.strip()
        full_id = raw_id.split('/abs/')[-1] if '/abs/' in raw_id else raw_id
        arxiv_id = full_id.split('v')[0]  # base ID for links
        published = entry.find('a:published', NS).text[:10]
        updated = entry.find('a:updated', NS).text[:10]
        authors = ', '.join(a.find('a:name', NS).text for a in entry.findall('a:author', NS))
        summary = entry.find('a:summary', NS).text.strip().replace('\n', ' ')
        cats = ', '.join(c.get('term') for c in entry.findall('a:category', NS))
        
        version = full_id[len(arxiv_id):] if full_id != arxiv_id else ""
        print(f"{i+1}. {title}")
        print(f"   ID: {arxiv_id}{version} | Published: {published} | Updated: {updated}")
        print(f"   Authors: {authors}")
        print(f"   Categories: {cats}")
        print(f"   Abstract: {summary[:300]}{'...' if len(summary) > 300 else ''}")
        print(f"   Links: https://arxiv.org/abs/{arxiv_id} | https://arxiv.org/pdf/{arxiv_id}")
        print()


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] in {"-h", "--help"}:
        print(__doc__)
        sys.exit(0)
    
    query = None
    author = None
    category = None
    ids = None
    max_results = 5
    sort = "relevance"
    
    i = 0
    positional = []
    while i < len(args):
        if args[i] == "--max" and i + 1 < len(args):
            max_results = int(args[i + 1]); i += 2
        elif args[i] == "--sort" and i + 1 < len(args):
            sort = args[i + 1]; i += 2
        elif args[i] == "--author" and i + 1 < len(args):
            author = args[i + 1]; i += 2
        elif args[i] == "--category" and i + 1 < len(args):
            category = args[i + 1]; i += 2
        elif args[i] == "--id" and i + 1 < len(args):
            ids = args[i + 1]; i += 2
        else:
            positional.append(args[i]); i += 1
    
    if positional:
        query = " ".join(positional)
    
    try:
        search(query=query, author=author, category=category, ids=ids,
               max_results=max_results, sort=sort)
    except RuntimeError as exc:
        print(f'[失败] 连续 {MAX_ATTEMPTS} 次请求 arXiv 均未成功：{exc}', file=sys.stderr)
        print('      最常见原因是 arXiv 对密集请求的临时限流（表现为 406），通常等待 1-2 分钟后重试即可。', file=sys.stderr)
        print('      这不是网络不通：同样的地址用 curl 往往能立刻返回 200。', file=sys.stderr)
        sys.exit(1)
