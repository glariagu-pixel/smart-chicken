import urllib.request
import json
import datetime

def fetch_market_data():
    # 使用 clist/get 接口，通过 fs=i:market.code 的方式指定多个指数
    # 1.000001: 上证指数
    # 0.399001: 深证成指
    # 0.399006: 创业板指
    # 1.000688: 科创50
    # 0.899050: 北证50
    ut = "bd1d9ddb040897f350c061f0674230d7"
    fs = "i:1.000001,i:0.399001,i:0.399006,i:1.000688,i:0.899050"
    fields = "f2,f3,f4,f5,f6,f12,f14"
    url = f"https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=10&po=1&np=1&ut={ut}&fltt=2&invt=2&fid=f3&fs={fs}&fields={fields}"
    
    try:
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data and data.get('data') and data['data'].get('diff'):
                indices = data['data']['diff']
                return indices
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def format_volume(volume):
    if volume >= 100000000:
        return f"{volume / 100000000:.2f} 亿"
    elif volume >= 10000:
        return f"{volume / 10000:.2f} 万"
    return str(volume)

def format_amount(amount):
    if amount >= 100000000:
        return f"{amount / 100000000:.2f} 亿"
    elif amount >= 10000:
        return f"{amount / 10000:.2f} 万"
    return str(amount)

def main():
    print(f"--- 东方财富今日大盘数据 ({datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}) ---")
    print(f"{'名称':<10} {'最新价':<10} {'涨跌幅':<10} {'涨跌额':<10} {'成交额':<10}")
    print("-" * 60)
    
    indices = fetch_market_data()
    if indices:
        for index in indices:
            name = index.get('f14', '-')
            price = index.get('f2', '-')
            change_percent = index.get('f3', '-')
            change_amount = index.get('f4', '-')
            amount = index.get('f6', 0)
            
            # 格式化涨跌幅
            change_percent_str = f"{change_percent:.2f}%" if isinstance(change_percent, (int, float)) else str(change_percent)
            if isinstance(change_percent, (int, float)) and change_percent > 0:
                change_percent_str = "+" + change_percent_str
                
            # 格式化涨跌额
            change_amount_str = f"{change_amount:.2f}" if isinstance(change_amount, (int, float)) else str(change_amount)
            if isinstance(change_amount, (int, float)) and change_amount > 0:
                change_amount_str = "+" + change_amount_str

            # 格式化最新价 (通常需要除以 100，但对于指数 API，有时直接是原始值，需验证)
            # 经查，东财 ulist/get 返回的 f2 通常已经是正确的小数形式，或者需要根据 dect 位处理。
            # 这里我们直接打印，如果不正确再调整。
            
            formatted_amount = format_amount(amount)
            
            print(f"{name:<10} {str(price):<10} {change_percent_str:<10} {change_amount_str:<10} {formatted_amount:<10}")
    else:
        print("未能获取到数据，请检查网络或 API 状态。")

if __name__ == "__main__":
    main()
