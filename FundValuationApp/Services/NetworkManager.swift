import Foundation

class NetworkManager {
    static let shared = NetworkManager()
    
    /// 从同花顺获取基金实时估值
    /// - Parameter code: 6位基金代码
    /// - Returns: (昨日净值, 实时估值, 涨跌幅)
    func fetchValuation(for code: String) async throws -> (prevJZ: Double, currGSZ: Double, change: Double)? {
        let urlString = "https://gz-fund.10jqka.com.cn/?module=api&controller=index&action=chart&info=vm_fd_\(code)&start=0930"
        guard let url = URL(string: urlString) else { return nil }
        
        var request = URLRequest(url: url)
        request.timeoutInterval = 10
        request.setValue("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1", forHTTPHeaderField: "User-Agent")
        request.setValue("https://fund.10jqka.com.cn/", forHTTPHeaderField: "Referer")
        
        let (data, _) = try await URLSession.shared.data(for: request)
        guard let content = String(data: data, encoding: .utf8) else { return nil }
        
        // 解析同花顺 JSONP 格式数据
        // 格式参考: vm_fd_163406='...|2026-01-30~2.2511~0930,0931,2.2528,2.2511,0.000;...'
        if content.contains("|") && content.contains("~") {
            let components = content.components(separatedBy: "|")
            if components.count > 1 {
                let mainPart = components[1]
                let headerLine = mainPart.components(separatedBy: ",")[0]
                let headerParts = headerLine.components(separatedBy: "~")
                
                if headerParts.count > 1 {
                    let prevJZ = Double(headerParts[1]) ?? 1.0
                    
                    let dataPoints = content.components(separatedBy: ",")
                    // 获取最后一个点的数据: 1500,2.28318,2.2511,0.000'
                    if let rawLastPoint = dataPoints.last {
                        let cleanedLastPoint = rawLastPoint.trimmingCharacters(in: CharacterSet(charactersIn: "'"))
                        let lastPointsInLine = cleanedLastPoint.components(separatedBy: ";")
                        if let lastPoint = lastPointsInLine.last {
                            let subParts = lastPoint.components(separatedBy: ",")
                            if subParts.count > 1 {
                                let currGSZ = Double(subParts[1]) ?? prevJZ
                                let change = ((currGSZ - prevJZ) / prevJZ) * 100
                                return (prevJZ, currGSZ, change)
                            }
                        }
                    }
                    
                    // 如果解析最后一个点失败，返回 Header 中的基准值
                    return (prevJZ, prevJZ, 0.0)
                }
            }
        }
        return nil
    }
}
