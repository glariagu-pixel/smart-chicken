import SwiftUI
import PhotosUI

struct ContentView: View {
    @State private var selectedItem: PhotosPickerItem? = nil
    @State private var selectedImage: UIImage? = nil
    @State private var fundItems: [FundItem] = []
    @State private var isLoading: Bool = false
    @State private var showResult: Bool = false
    
    var body: some View {
        NavigationView {
            VStack {
                if let image = selectedImage {
                    Image(uiImage: image)
                        .resizable()
                        .scaledToFit()
                        .frame(maxHeight: 300)
                        .cornerRadius(12)
                        .shadow(radius: 5)
                        .padding()
                } else {
                    VStack(spacing: 20) {
                        Image(systemName: "doc.text.viewfinder")
                            .font(.system(size: 80))
                            .foregroundColor(.blue)
                        Text("请上传您的基金持仓截图")
                            .font(.title3)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxHeight: 300)
                    .padding()
                }
                
                Spacer()
                
                PhotosPicker(selection: $selectedItem, matching: .images) {
                    HStack {
                        Image(systemName: "photo.badge.plus")
                        Text("选择截图进行智能分析")
                    }
                    .font(.headline)
                    .frame(maxWidth: .infinity)
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(15)
                    .padding(.horizontal)
                }
                .onChange(of: selectedItem) { newItem in
                    Task {
                        if let data = try? await newItem?.loadTransferable(type: Data.self),
                           let image = UIImage(data: data) {
                            selectedImage = image
                            await analyzeImage(image)
                        }
                    }
                }
                
                if isLoading {
                    VStack {
                        ProgressView()
                            .scaleEffect(1.5)
                        Text("正在识别并查询实时估值...")
                            .font(.caption)
                            .padding(.top, 10)
                    }
                    .padding()
                }
                
                List {
                    if !fundItems.isEmpty {
                        Section(header: Text("识别到的基金明细")) {
                            ForEach(fundItems) { item in
                                FundRowView(item: item)
                            }
                        }
                        
                        Section(header: Text("盈亏统计")) {
                            let totalProfit = fundItems.reduce(0) { $0 + $1.realtimeProfit }
                            let totalAmount = fundItems.reduce(0) { $0 + $1.holdingAmount }
                            
                            HStack {
                                Text("总持仓金额")
                                Spacer()
                                Text(String(format: "%.2f 元", totalAmount))
                                    .bold()
                            }
                            
                            HStack {
                                Text("今日预估收益")
                                Spacer()
                                Text(String(format: "%+.2f 元", totalProfit))
                                    .foregroundColor(totalProfit >= 0 ? .red : .green)
                                    .bold()
                            }
                        }
                    }
                }
                .listStyle(InsetGroupedListStyle())
            }
            .navigationTitle("养基宝手搓版")
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    if !fundItems.isEmpty {
                        Button("刷新") {
                            if let image = selectedImage {
                                Task { await analyzeImage(image) }
                            }
                        }
                    }
                }
            }
        }
    }
    
    /// 分析图片并请求实时数据
    func analyzeImage(_ image: UIImage) async {
        isLoading = true
        // 1. OCR 识别
        do {
            let detected = try await OCRService.shared.recognizeFundData(from: image)
            
            // 2. 并行获取每只基金的实时估值
            var updatedItems: [FundItem] = []
            
            // 为了提高效率，这里可以使用 TaskGroup
            await withTaskGroup(of: FundItem?.self) { group in
                for var item in detected {
                    group.addTask {
                        do {
                            if let valuation = try await NetworkManager.shared.fetchValuation(for: item.code) {
                                var newItem = item
                                newItem.prevNetValue = valuation.prevJZ
                                newItem.currentValuation = valuation.currGSZ
                                newItem.realtimeChange = valuation.change
                                
                                // 盈亏计算逻辑：
                                // 份额 = 上日收盘金额 / 上日净值
                                let shares = newItem.holdingAmount / valuation.prevJZ
                                // 今日收益 = 份额 * (当前估值 - 上日净值)
                                newItem.realtimeProfit = shares * (valuation.currGSZ - valuation.prevJZ)
                                return newItem
                            }
                        } catch {
                            print("获取 \(item.name) 估值失败: \(error)")
                        }
                        return item
                    }
                }
                
                for await result in group {
                    if let res = result {
                        updatedItems.append(res)
                    }
                }
            }
            
            // 按金额降序排列
            fundItems = updatedItems.sorted { $0.holdingAmount > $1.holdingAmount }
        } catch {
            print("OCR 失败: \(error)")
        }
        isLoading = false
    }
}

struct FundRowView: View {
    let item: FundItem
    
    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(item.name)
                    .font(.headline)
                    .lineLimit(1)
                Spacer()
                Text(item.code)
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            HStack(spacing: 0) {
                VStack(alignment: .leading) {
                    Text("实时涨幅").font(.caption2).foregroundColor(.secondary)
                    Text(item.changeString)
                        .font(.subheadline)
                        .bold()
                        .foregroundColor(item.realtimeChange >= 0 ? .red : .green)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                
                VStack(alignment: .leading) {
                    Text("实时收益").font(.caption2).foregroundColor(.secondary)
                    Text(item.profitString)
                        .font(.subheadline)
                        .bold()
                        .foregroundColor(item.realtimeProfit >= 0 ? .red : .green)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                
                VStack(alignment: .trailing) {
                    Text("持仓金额").font(.caption2).foregroundColor(.secondary)
                    Text(String(format: "%.2f", item.holdingAmount))
                        .font(.subheadline)
                }
                .frame(maxWidth: .infinity, alignment: .trailing)
            }
            
            HStack {
                Text("持有收益: \(String(format: "%+.2f", item.holdProfit))")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}
