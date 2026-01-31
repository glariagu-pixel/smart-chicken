import Foundation
import Vision
import UIKit

class OCRService {
    static let shared = OCRService()
    
    /// 从图片中识别基金数据
    /// - Parameter image: 用户上传的截图
    /// - Returns: 识别到的 FundItem 列表
    func recognizeFundData(from image: UIImage) async throws -> [FundItem] {
        guard let cgImage = image.cgImage else { return [] }
        
        return try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: error)
                    return
                }
                
                guard let observations = request.results as? [VNRecognizedTextObservation] else {
                    continuation.resume(returning: [])
                    return
                }
                
                // 1. 将 OCR 结果按 Y 轴坐标（即行）进行初步分组
                // 翻转坐标系，因为 Vision 的原点在左下角，而通常阅读习惯是从上往下
                let sortedObservations = observations.sorted { $0.boundingBox.midY > $1.boundingBox.midY }
                
                var rowGroups: [[VNRecognizedTextObservation]] = []
                var currentRow: [VNRecognizedTextObservation] = []
                var lastMidY: CGFloat = -1
                
                let rowThreshold: CGFloat = 0.02 // 同一行的 Y 轴偏移阈值
                
                for obs in sortedObservations {
                    let midY = obs.boundingBox.midY
                    if lastMidY == -1 || abs(midY - lastMidY) < rowThreshold {
                        currentRow.append(obs)
                    } else {
                        rowGroups.append(currentRow)
                        currentRow = [obs]
                    }
                    lastMidY = midY
                }
                if !currentRow.isEmpty {
                    rowGroups.append(currentRow)
                }
                
                // 2. 解析每一行的数据
                var detectedItems: [FundItem] = []
                
                for row in rowGroups {
                    // 合并该行的所有文本片段，按 X 轴排序以保持阅读顺序
                    let lineText = row.sorted { $0.boundingBox.minX < $1.boundingBox.minX }
                        .compactMap { $0.topCandidates(1).first?.string }
                        .joined(separator: " ")
                    
                    // 3. 匹配基金名称
                    for (name, code) in FundDataStore.nameToCodeMap {
                        if lineText.contains(name) {
                            var item = FundItem(name: name, code: code)
                            
                            // 匹配金额模式 (支持带逗号的千分位和两位小数，如 1,649.77)
                            // 注意：收益可能有正负号
                            let pricePattern = "[+-]?\\d{1,3}(,\\d{3})*(\\.\\d{2})"
                            if let regex = try? NSRegularExpression(pattern: pricePattern) {
                                let results = regex.matches(in: lineText, range: NSRange(lineText.startIndex..., in: lineText))
                                let matches = results.map { String(lineText[Range($0.range, in: lineText)!]) }
                                
                                // 根据之前的观察：
                                // 第一个出现的金额通常是“持仓金额”
                                // 第二个出现的带正负号的通常是“昨日收益”或“持有收益”
                                // 这里我们优先提取金额较大的作为持仓金额
                                var numericValues = matches.compactMap { Double($0.replacingOccurrences(of: ",", with: "")) }
                                
                                if let maxAmount = numericValues.max() {
                                    item.holdingAmount = maxAmount
                                    // 从列表中移除最大值，剩余的可能就是持有收益
                                    if let index = numericValues.firstIndex(of: maxAmount) {
                                        numericValues.remove(at: index)
                                        if let firstRemaining = numericValues.first {
                                            item.holdProfit = firstRemaining
                                        }
                                    }
                                }
                            }
                            detectedItems.append(item)
                            break
                        }
                    }
                }
                
                continuation.resume(returning: detectedItems)
            }
            
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true
            request.recognitionLanguages = ["zh-Hans", "en-US"]
            
            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])
            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: error)
            }
        }
    }
}
