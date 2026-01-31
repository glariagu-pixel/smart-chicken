import urllib.request
import json

# 生成 100 条模拟基金数据文本
funds_text = ""
for i in range(1, 101):
    code = str(i).zfill(6)
    amount = 1000 + i * 10
    funds_text += f"{code} {amount}\n"

url = "http://localhost:8000/api/resolve"
data = json.dumps({"text": funds_text}).encode('utf-8')

req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

try:
    print(f"正在测试发送 100 条基金数据到 {url}...")
    with urllib.request.urlopen(req, timeout=60) as response:
        res_data = json.loads(response.read().decode('utf-8'))
        
        recognized = res_data.get("data", [])
        print(f"测试完成！")
        print(f"发送条数: 100")
        print(f"成功识别并获取到实时数据的条数: {len(recognized)}")
        
        if len(recognized) > 0:
            print("前 3 条识别结果示例:")
            for item in recognized[:3]:
                print(f" - {item['name']} ({item['code']}): 金额 {item['amount']}, 涨跌 {item['realtimeChange']}%")
        else:
            print("警告: 未能识别到任何有效基金数据。")

except Exception as e:
    print(f"测试过程中发生错误: {e}")
