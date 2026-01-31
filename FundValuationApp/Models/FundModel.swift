import Foundation

struct FundItem: Identifiable, Codable {
    var id = UUID()
    var name: String            // 基金名称
    var code: String            // 基金编号
    var realtimeChange: Double = 0.0 // 实时涨幅 (%)
    var realtimeProfit: Double = 0.0 // 实时收益
    var holdProfit: Double = 0.0     // 持有收益 (图片中的历史累计)
    var holdingAmount: Double = 0.0  // 持仓金额 (上一工作日结算金额)
    
    // 原始净值数据，用于内部计算
    var prevNetValue: Double = 1.0
    var currentValuation: Double = 1.0
    
    var changeString: String {
        let sign = realtimeChange >= 0 ? "+" : ""
        return "\(sign)\(String(format: "%.2f", realtimeChange))%"
    }
    
    var profitString: String {
        let sign = realtimeProfit >= 0 ? "+" : ""
        return "\(sign)\(String(format: "%.2f", realtimeProfit))"
    }
}

class FundDataStore {
    // 简单的名称到代码的映射表，生产环境中可扩展
    static let nameToCodeMap: [String: String] = [
        "博时黄金ETF联接A": "002610",
        "永赢半导体产业智选混合C": "015968",
        "国泰黄金ETF联接C": "004253",
        "银华集成电路混合C": "013841",
        "易方达储能电池ETF联接C": "021034",
        "华夏有色金属ETF联接D": "021534",
        "兴全合润混合A": "163406",
        "广发多因子混合": "002943",
        "易方达优质企业三年持有期混合": "009342"
    ]
    
    static func getCode(for name: String) -> String? {
        return nameToCodeMap[name]
    }
}
