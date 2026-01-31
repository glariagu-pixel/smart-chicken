import os
import re
import json
import urllib.request
import urllib.parse
import datetime
import uvicorn
import asyncio
from typing import List
from pydantic import BaseModel
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 基金名称到代码的缓存
FUND_CACHE = {
    "博时黄金ETF联接A": "002610",
    "永赢半导体产业智选混合C": "015968",
    "国泰黄金ETF联接C": "004253",
    "银华集成电路混合C": "013841",
    "易方达储能电池ETF联接C": "021034",
    "华夏有色金属ETF联接D": "021534",
    "兴全合润混合A": "163406",
    "广发多因子混合": "002943",
    "易方达优质企业三年持有期混合": "009342",
    "鹏华丰享债券": "003401",
    "广发纯债债券C": "270049",
    "永赢医药创新智选": "015915",
    "易方达沪深300ETF联接A": "110020",
    "天弘恒生科技ETF联接A": "012804",
    "广发纳斯达克100ETF联接(QDII)C": "006479",
    "永赢先进制造智选混合C": "015911",
    "永赢高端装备智选混合A": "015912",
    "永赢高端装备智选混合C": "015913",
    "永赢信息产业智选混合C": "015917",
    "嘉实中证稀土产业ETF联接C": "011036",
    "永赢医药创新智选混合C": "015915",
    "易方达均衡成长股票": "008985",
    "广发全球医疗保健指数(QDII)A": "000369",
    "招商纳斯达克100ETF发起式联接": "016055",
    "南方标普中国A股大盘红利低波": "008163",
    "国富亚洲机会股票(QDII)C": "008240",
    "摩根纳斯达克100指数(QDII)C": "017116",
    "摩根纳斯达克100指数(QDII)A": "017115",
    "摩根标普500指数(QDII)A": "017641"
}

def search_fund_by_name(keyword):
    """从天天基金公开接口搜索基金代码"""
    if keyword in FUND_CACHE:
        return FUND_CACHE[keyword], keyword
    
    # 清理关键词
    keyword = keyword.strip().replace(' ', '')
    if len(keyword) < 2: return None, None
    
    url = f"https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?m=1&key={urllib.parse.quote(keyword)}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if res_data.get('Datas') and len(res_data['Datas']) > 0:
                # 匹配最接近的一个
                best_match = res_data['Datas'][0]
                code = best_match.get('CODE')
                name = best_match.get('NAME')
                if code:
                    FUND_CACHE[keyword] = code
                    return code, name
    except Exception as e:
        print(f"搜索基金失败 {keyword}: {e}")
    return None, None

def get_fund_info_ths(fund_code):
    """从同花顺获取基金实时估值"""
    url = f"https://gz-fund.10jqka.com.cn/?module=api&controller=index&action=chart&info=vm_fd_{fund_code}&start=0930"
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
        'Referer': 'https://fund.10jqka.com.cn/'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            if '|' in content and '~' in content:
                main_part = content.split('|')[1]
                header = main_part.split(',')[0]
                parts = header.split('~')
                
                data_points = content.split(',')
                last_point = data_points[-1].strip("'").split(';')[-1]
                last_val = last_point.split(',')[1] if ',' in last_point else parts[1]
                
                prev_jz = float(parts[1])
                curr_gsz = float(last_val)
                gszzl = ((curr_gsz - prev_jz) / prev_jz) * 100
                
                return {
                    'code': fund_code,
                    'prevJZ': prev_jz,
                    'currGSZ': curr_gsz,
                    'gszzl': gszzl,
                    'gztime': parts[0] + " " + (last_point.split(',')[0] if ',' in last_point else "实时")
                }
    except Exception as e:
        print(f"Error fetching THS data for {fund_code}: {e}")
    return None

from typing import List

from pydantic import BaseModel

class ResolveRequest(BaseModel):
    text: str

import asyncio
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(max_workers=20)

def fetch_single_fund_sync(fund_code, amount):
    """同步抓取单支基金数据的包装函数"""
    live_data = get_fund_info_ths(fund_code)
    if live_data:
        shares = amount / live_data['prevJZ'] if amount > 0 else 0
        realtime_profit = shares * (live_data['currGSZ'] - live_data['prevJZ'])
        # 优先从缓存获取名称，否则使用默认名称
        matched_name = next((name for name, c in FUND_CACHE.items() if c == fund_code), f"基金({fund_code})")
        return {
            "name": matched_name,
            "code": fund_code,
            "realtimeChange": round(live_data['gszzl'], 2),
            "realtimeProfit": round(realtime_profit, 2),
            "holdProfit": 0.0,
            "amount": amount
        }
    return None

@app.post("/api/resolve")
async def resolve_text(req: ResolveRequest):
    # 处理各种分隔符
    raw_text = req.text.replace('：', ':').replace('元', '').replace('（', '(').replace('）', ')')
    lines = raw_text.split('\n')
    
    to_fetch = []
    loop = asyncio.get_event_loop()
    
    for line in lines:
        line = line.strip()
        if not line: continue
        
        found_code = None
        found_name = None
        search_text = line
        
        # 1. 优先尝试提取 6 位连续数字作为代码
        code_match = re.search(r'\b\d{6}\b', line)
        if code_match:
            found_code = code_match.group(0)
            # 尝试获取名称
            found_name = next((name for name, c in FUND_CACHE.items() if c == found_code), f"基金({found_code})")
            search_text = line[code_match.end():]
        else:
            # 2. 尝试从行中提取潜在的基金名称并搜索
            # 匹配模式：[序号.] 基金名称 [:：\s] 金额
            # 排除掉行首的数字序号，提取中间的非数字字符串作为关键词
            name_match = re.search(r'^\s*(?:\d+[\.、\s]+)?(.*?)\s*[:：\s]\s*(\d.*)$', line)
            if name_match:
                potential_name = name_match.group(1).strip()
                if potential_name:
                    print(f"尝试公开搜索基金: {potential_name}")
                    found_code, found_name = search_fund_by_name(potential_name)
                    search_text = name_match.group(2)
        
        # 如果还是没找到，尝试在全行中匹配已知缓存（兼容短名称）
        if not found_code:
            clean_line = line.replace(" ", "")
            sorted_names = sorted(FUND_CACHE.items(), key=lambda x: len(x[0]), reverse=True)
            for name, c in sorted_names:
                if name.replace(" ", "") in clean_line:
                    found_name = name
                    found_code = c
                    # 尝试定位金额搜索区域
                    match_pos = line.find(name[:4])
                    if match_pos != -1:
                        search_text = line[match_pos + len(name):]
                    break
        
        if found_code:
            # 3. 提取金额
            nums = re.findall(r'[+-]?\d[\d,]*\.?\d+', search_text)
            amount = 0.0
            for n in reversed(nums):
                val_str = n.replace(',', '')
                if val_str == found_code: continue
                try:
                    val = float(val_str)
                    if val > 0.1:
                        amount = val
                        break
                except: continue
            
            to_fetch.append((found_code, found_name, amount))

    if not to_fetch:
        return {"data": []}
        
    def fetch_with_name(code, name, amt):
        try:
            live_data = get_fund_info_ths(code)
            if live_data:
                shares = amt / live_data['prevJZ'] if amt > 0 else 0
                realtime_profit = shares * (live_data['currGSZ'] - live_data['prevJZ'])
                return {
                    "name": name,
                    "code": code,
                    "realtimeChange": round(live_data['gszzl'], 2),
                    "realtimeProfit": round(realtime_profit, 2),
                    "holdProfit": 0.0,
                    "amount": amt,
                    "status": "success"
                }
        except: pass
        return {
            "name": name,
            "code": code,
            "realtimeChange": 0.0,
            "realtimeProfit": 0.0,
            "holdProfit": 0.0,
            "amount": amt,
            "status": "partial"
        }

    futures = [loop.run_in_executor(executor, fetch_with_name, c, n, a) for c, n, a in to_fetch]
    results = await asyncio.gather(*futures)
    
    resolved_funds = [r for r in results if r is not None]
    print(f"解析完成：提交 {len(to_fetch)} 条，成功返回 {len(resolved_funds)} 条")
    return {"data": resolved_funds}

@app.post("/api/refresh")
async def refresh_funds(funds: List[dict]):
    """并行刷新持仓列表"""
    loop = asyncio.get_event_loop()
    futures = [loop.run_in_executor(executor, fetch_single_fund_sync, f['code'], f['amount']) for f in funds]
    results = await asyncio.gather(*futures)
    updated_funds = [r if r else f for r, f in zip(results, funds)]
    return {"data": updated_funds}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
