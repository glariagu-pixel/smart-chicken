import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Plus, Trash2, RefreshCw, TrendingUp, TrendingDown, DollarSign } from 'lucide-react';
import toast, { Toaster } from 'react-hot-toast';

interface FundData {
  name: string;
  code: string;
  realtimeChange: number;
  realtimeProfit: number;
  holdProfit: number;
  amount: number;
}

// 获取 API 基础路径，优先使用环境变量，本地开发默认使用 8000 端口
const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const App: React.FC = () => {
  const [inputText, setInputText] = useState('');
  const [data, setData] = useState<FundData[]>([]);
  const [loading, setLoading] = useState(false);

  // 1. 初始化时从 localStorage 加载数据
  useEffect(() => {
    const saved = localStorage.getItem('fund_holdings');
    if (saved) {
      const parsed = JSON.parse(saved);
      setData(parsed);
      // 加载后自动刷新一次实时数据
      refreshAll(parsed);
    }
  }, []);

  // 2. 数据变动时保存到 localStorage
  useEffect(() => {
    localStorage.setItem('fund_holdings', JSON.stringify(data));
  }, [data]);

  const refreshAll = async (currentData: FundData[]) => {
    if (currentData.length === 0) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/refresh`, currentData);
      setData(res.data.data);
    } catch (err) {
      toast.error('刷新实时数据失败');
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/api/resolve`, { text: inputText });
      const newFunds = res.data.data;
      if (newFunds.length > 0) {
        // 合并新旧持仓，如果代码相同则更新
        setData(prev => {
          const updated = [...prev];
          newFunds.forEach((nf: FundData) => {
            const idx = updated.findIndex(f => f.code === nf.code);
            if (idx > -1) {
              updated[idx] = nf;
            } else {
              updated.push(nf);
            }
          });
          return updated;
        });
        toast.success(`识别成功！添加了 ${newFunds.length} 支基金`);
        setInputText('');
      } else {
        toast.error('未识别到有效的基金名称或代码，请检查输入格式。');
      }
    } catch (err) {
      toast.error('解析失败，请检查后端状态。');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (code: string) => {
    setData(prev => prev.filter(f => f.code !== code));
    toast.success('已删除');
  };

  const totalProfit = data.reduce((acc, curr) => acc + curr.realtimeProfit, 0);
  const totalAmount = data.reduce((acc, curr) => acc + curr.amount, 0);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center p-4">
      <Toaster />
      <header className="w-full max-w-md bg-blue-600 text-white p-5 rounded-2xl shadow-lg mb-4 text-center">
        <h1 className="text-xl font-bold">聪明养鸡 (Web)</h1>
        <p className="text-blue-100 text-xs mt-1">粘贴或输入：基金名 金额 (支持多行)</p>
      </header>

      <main className="w-full max-w-md flex flex-col gap-4">
        {/* 文本输入区域 */}
        <div className="bg-white p-4 rounded-2xl shadow-sm border border-gray-100 flex flex-col gap-3">
          <textarea
            className="w-full h-24 p-3 bg-gray-50 rounded-xl border-none focus:ring-2 focus:ring-blue-500 text-sm"
            placeholder="示例：&#10;华夏有色 5000&#10;021534 3200"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
          />
          <button
            onClick={handleAdd}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 rounded-xl font-bold flex items-center justify-center gap-2 active:bg-blue-700 disabled:opacity-50"
          >
            {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : <Plus className="w-5 h-5" />}
            添加/更新持仓
          </button>
        </div>

        {/* 持仓列表 */}
        {data.length > 0 && (
          <div className="flex flex-col gap-3">
            <div className="flex justify-between items-center px-1">
              <h2 className="text-sm font-bold text-gray-700">当前持仓 ({data.length})</h2>
              <button 
                onClick={() => refreshAll(data)} 
                className="text-blue-600 text-xs flex items-center gap-1"
                disabled={loading}
              >
                <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} /> 刷新行情
              </button>
            </div>
            
            <div className="bg-white rounded-2xl shadow-sm overflow-hidden border border-gray-100">
              <table className="w-full text-left">
                <thead className="bg-gray-50 text-gray-500 text-[10px]">
                  <tr>
                    <th className="px-3 py-2 font-medium">基金与持仓</th>
                    <th className="px-3 py-2 font-medium text-right">实时估值</th>
                    <th className="px-3 py-2 font-medium text-center">操作</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 text-xs">
                  {data.map((fund) => (
                    <tr key={fund.code} className="hover:bg-gray-50">
                      <td className="px-3 py-2">
                        <div className="font-bold text-gray-800 truncate w-28">{fund.name}</div>
                        <div className="text-[10px] text-gray-500 mt-0.5 flex items-center gap-1">
                          <span className="bg-gray-100 px-1 rounded">{fund.code}</span>
                          <span className="text-gray-400 font-medium">¥{fund.amount.toFixed(0)}</span>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-right">
                        <div className={`font-bold ${fund.realtimeProfit >= 0 ? 'text-red-500' : 'text-green-600'}`}>
                          {fund.realtimeProfit >= 0 ? '+' : ''}{fund.realtimeProfit.toFixed(1)}
                        </div>
                        <div className={`text-[10px] font-medium ${fund.realtimeChange >= 0 ? 'text-red-500' : 'text-green-600'}`}>
                          {fund.realtimeChange >= 0 ? '+' : ''}{fund.realtimeChange}%
                        </div>
                      </td>
                      <td className="px-3 py-2 text-center">
                        <button onClick={() => handleDelete(fund.code)} className="p-2 text-gray-300 hover:text-red-500">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* 统计卡片 */}
            <div className="grid grid-cols-2 gap-3">
              <div className="bg-white p-3 rounded-2xl shadow-sm border border-gray-100">
                <p className="text-[10px] text-gray-400 mb-0.5">总持仓金额</p>
                <p className="text-base font-bold text-gray-800">{totalAmount.toFixed(0)}</p>
              </div>
              <div className={`p-3 rounded-2xl shadow-sm border ${totalProfit >= 0 ? 'bg-red-50 border-red-100' : 'bg-green-50 border-green-100'}`}>
                <p className={`text-[10px] mb-0.5 ${totalProfit >= 0 ? 'text-red-400' : 'text-green-400'}`}>今日预估盈亏</p>
                <p className={`text-base font-bold ${totalProfit >= 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(1)}
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer className="mt-auto py-6 text-gray-400 text-[10px]">
        &copy; 2026 聪明养鸡 Web 版 | 本地存储，隐私安全
      </footer>
    </div>
  );
};

export default App;
