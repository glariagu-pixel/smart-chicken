import urllib.request
import json
import re
import datetime

def get_fund_info(fund_code):
    """获取基金基础信息及昨日净值"""
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
    try:
        with urllib.request.urlopen(url) as response:
            content = response.read().decode('utf-8')
            # 匹配 jsonpgz({...});
            match = re.search(r'jsonpgz\((.*)\);', content)
            if match:
                data = json.loads(match.group(1))
                return data
    except Exception as e:
        print(f"获取基金信息失败: {e}")
    return None

def get_stock_changes(stock_list):
    """获取股票实时涨跌幅"""
    # stock_list 格式如: ['1.601899', '0.002460']
    secids = ",".join(stock_list)
    ut = "bd1d9ddb040897f350c061f0674230d7"
    fields = "f12,f14,f2,f3,f4"
    url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=20&po=1&np=1&ut={ut}&fltt=2&invt=2&fid=f3&fs=i:{secids.replace(',', ',i:')}&fields={fields}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data and data.get('data') and data['data'].get('diff'):
                return data['data']['diff']
    except Exception as e:
        print(f"获取股票信息失败: {e}")
    return []

def calculate_valuation(fund_code, holdings):
    """
    计算基金估值
    holdings: [{'code': '601899', 'name': '紫金矿业', 'weight': 15.30}, ...]
    """
    fund_info = get_fund_info(fund_code)
    if not fund_info:
        return
    
    prev_jz = float(fund_info['dwjz'])
    prev_date = fund_info['jzrq']
    fund_name = fund_info['name']
    
    stock_codes = []
    for h in holdings:
        # 东财代码前缀: 6开头为1.，0或3开头为0.
        prefix = "1." if h['code'].startswith('6') else "0."
        stock_codes.append(f"{prefix}{h['code']}")
    
    stock_data = get_stock_changes(stock_codes)
    stock_map = {s['f12']: s for s in stock_data}
    
    print(f"\n--- {fund_name} ({fund_code}) 实时估值计算 ---")
    print(f"基准日期: {prev_date}  单位净值: {prev_jz}")
    print("-" * 60)
    print(f"{'成分股':<10} {'权重':<10} {'今日涨跌':<10} {'贡献度':<10}")
    
    total_weight = 0
    weighted_change_sum = 0
    
    for h in holdings:
        code = h['code']
        weight = h['weight']
        s_info = stock_map.get(code)
        
        if s_info:
            change = s_info['f3'] # 涨跌幅
            contribution = (change * weight) / 100
            weighted_change_sum += change * weight
            total_weight += weight
            print(f"{h['name']:<10} {weight:>6.2f}% {change:>9.2f}% {contribution:>9.2f}%")
        else:
            print(f"{h['name']:<10} {weight:>6.2f}% {'未获取':>10}")

    if total_weight > 0:
        # 估算总涨跌幅 (按已知权重部分同比例放大)
        est_change_percent = weighted_change_sum / total_weight
        # 注意: 这里的 est_change_percent 是基于已知持仓部分的平均涨跌。
        # 实际估值通常会乘以基金的总股票仓位。联接基金仓位通常接近 95% - 100%。
        # 我们这里假设整体涨跌等于前十大加权涨跌。
        
        est_jz = prev_jz * (1 + est_change_percent / 100)
        
        print("-" * 60)
        print(f"前十大总权重: {total_weight:.2f}%")
        print(f"前十大加权涨跌: {est_change_percent:.2f}%")
        print(f"实时估算净值: {est_jz:.4f}")
        print(f"官方估算涨跌: {fund_info['gszzl']}% (参考)")
        print(f"估值时间: {fund_info['gztime']}")

def get_fund_info_ths(fund_code):
    """从同花顺获取基金实时估值"""
    url = f"https://gz-fund.10jqka.com.cn/?module=api&controller=index&action=chart&info=vm_fd_{fund_code}&start=0930"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Referer': 'https://fund.10jqka.com.cn/'
    }
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            # 解析格式: vm_fd_163406='...|2026-01-30~2.2511~0930,数据点...'
            if '|' in content and '~' in content:
                main_part = content.split('|')[1]
                header = main_part.split(',')[0] # 2026-01-30~2.2511~0930
                parts = header.split('~')
                
                # 获取最后一个数据点作为实时估值
                data_points = content.split(',')
                last_point = data_points[-1].strip("'").split(';')[-1] # 1500,2.28318,2.2511,0.000
                last_val = last_point.split(',')[1] if ',' in last_point else parts[1]
                
                prev_jz = float(parts[1])
                curr_gsz = float(last_val)
                gszzl = ((curr_gsz - prev_jz) / prev_jz) * 100
                
                return {
                    'fundcode': fund_code,
                    'name': f"基金{fund_code}(同花顺)",
                    'dwjz': str(prev_jz),
                    'gsz': str(round(curr_gsz, 4)),
                    'gszzl': str(round(gszzl, 2)),
                    'gztime': parts[0] + " " + (last_point.split(',')[0] if ',' in last_point else "实时")
                }
    except Exception as e:
        print(f"获取同花顺数据失败 ({fund_code}): {e}")
    return None

def get_fund_valuation_only(fund_codes, source="ths"):
    """仅获取基金实时估值"""
    print(f"\n--- 基金实时估值汇总 ({source.upper()}数据源, {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"{'代码':<10} {'基金名称':<25} {'估值':<10} {'涨跌幅':<10} {'时间':<10}")
    print("-" * 80)
    
    results = []
    for code in fund_codes:
        info = get_fund_info_ths(code) if source == "ths" else get_fund_info(code)
        if info:
            name = info['name']
            gsz = info['gsz']
            gszzl = info['gszzl']
            gztime = info['gztime']
            print(f"{code:<10} {name:<25} {gsz:<10} {gszzl:>6}%  {gztime:<10}")
            results.append(f"{code}, {name}, {gsz}, {gszzl}%, {gztime}")
    
    # 将结果保存到文本文件
    with open("基金估值结果.txt", "w", encoding="utf-8") as f:
        f.write("代码, 基金名称, 估值, 涨跌幅, 时间\n")
        f.write("\n".join(results))
    print(f"\n结果已保存至: 基金估值结果.txt")

def calculate_holdings_and_profit(image_data, source="ths"):
    """
    根据图片数据计算持有份额、实时涨跌幅、实时盈亏
    image_data: [{'name': '...', 'amount': 1649.77, 'code': '002610'}, ...]
    """
    print(f"\n--- 基金持有盈亏实时分析 ({source.upper()}数据源, {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    
    # 规范化输出表头
    header_list = ["基金名称", "基金编号", "实时涨幅", "实时收益", "持有收益", "持仓金额"]
    header_format = "{:<22} {:<10} {:>10} {:>10} {:>10} {:>10}"
    print(header_format.format(*header_list))
    print("-" * 95)
    
    file_results = [header_format.format(*header_list), "-" * 95]
    total_realtime_profit = 0
    total_last_amount = 0
    
    for item in image_data:
        info = get_fund_info_ths(item['code']) if source == "ths" else get_fund_info(item['code'])
        if info:
            prev_jz = float(info['dwjz'])      # 上一交易日净值
            curr_gsz = float(info['gsz'])      # 实时估算净值
            gszzl = float(info['gszzl'])       # 实时涨幅
            
            # 持仓金额 (上一工作日结算金额)
            last_amount = item['amount']
            total_last_amount += last_amount
            
            # 份额 = 上一交易日收盘金额 / 上一交易日净值
            shares = last_amount / prev_jz
            
            # 实时收益 = 份额 * (实时估值 - 上一交易日净值)
            realtime_profit = shares * (curr_gsz - prev_jz)
            total_realtime_profit += realtime_profit
            
            # 持有收益 (图片中的历史累计收益 + 今日实时收益)
            # 注意：此处图片显示的“持有收益”是截止上个交易日的累计值
            # 完整输出时，我们将实时收益和持仓金额展示出来
            # 考虑到用户需求样式，我们将“持有收益”列作为预留或展示实时变动
            
            # 使用图片中的准确名称
            name_display = item['name']
            
            line = header_format.format(
                name_display,
                item['code'],
                f"{gszzl:>+7.2f}%",
                f"{realtime_profit:>+8.2f}",
                f"{item['hold_profit']:>+8.2f}", # 使用图片中的历史持有收益
                f"{last_amount:>10.2f}"
            )
            print(line)
            file_results.append(line)
        else:
            error_line = f"{item['name']:<15} {item['code']:<10} {'获取失败':<10}"
            print(error_line)
            file_results.append(error_line)
    
    footer = f"\n当日合计实时收益预估: {total_realtime_profit:>+10.2f} 元 | 总持仓金额: {total_last_amount:>10.2f} 元"
    print("-" * 95)
    print(footer)
    file_results.append("-" * 95)
    file_results.append(footer)
    
    # 覆盖写入结果文件
    with open("基金估值结果.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(file_results))
    print(f"\n规范化结果已覆盖写入: 基金估值结果.txt")

if __name__ == "__main__":
    # 解析图片数据 (增加持有收益字段以符合输出规范)
    image_holdings = [
        {'name': '博时黄金ETF联接A', 'amount': 1649.77, 'code': '002610', 'hold_profit': 255.22},
        {'name': '永赢半导体产业智选混合C', 'amount': 2049.95, 'code': '015968', 'hold_profit': 39.57},
        {'name': '国泰黄金ETF联接C', 'amount': 8957.61, 'code': '004253', 'hold_profit': 2695.65},
        {'name': '银华集成电路混合C', 'amount': 2730.74, 'code': '013841', 'hold_profit': 180.74},
        {'name': '易方达储能电池ETF联接C', 'amount': 3565.30, 'code': '021034', 'hold_profit': -57.62},
        {'name': '华夏有色金属ETF联接D', 'amount': 2373.1, 'code': '021534', 'hold_profit': 215.34} # 华夏数据根据图表估算
    ]
    
    calculate_holdings_and_profit(image_holdings, source="ths")

    # 之前的成分股估值计算示例
    holdings_021534 = [
        {'code': '601899', 'name': '紫金矿业', 'weight': 15.30},
        {'code': '603993', 'name': '洛阳钼业', 'weight': 7.92},
        {'code': '600111', 'name': '北方稀土', 'weight': 5.30},
        {'code': '603799', 'name': '华友钴业', 'weight': 4.69},
        {'code': '601600', 'name': '中国铝业', 'weight': 4.39},
        {'code': '002460', 'name': '赣锋锂业', 'weight': 3.23},
        {'code': '600547', 'name': '山东黄金', 'weight': 3.18},
        {'code': '000807', 'name': '云铝股份', 'weight': 3.11},
        {'code': '600489', 'name': '中金黄金', 'weight': 3.08},
        {'code': '002466', 'name': '天齐锂业', 'weight': 2.60},
    ]
    calculate_valuation("021534", holdings_021534)
