import pandas as pd
import os
from collections import defaultdict

class ExcelReader:
    def __init__(self, data_dir="."):
        self.data_dir = data_dir
        # stock_map: 用于根据代码和年份查找 URL -> key: "code_year", value: url
        self.stock_map = {} 
        # stock_db: 用于搜索建议，存储 [{'code': '...', 'name': '...'}, ...]
        self.stock_db = []
        # stock_years: 存储每个股票拥有的年份 -> key: code, value: set(years)
        self.stock_years = defaultdict(set)
        
        self._load_data()

    def _load_data(self):
        """加载 Excel/CSV 数据，建立索引和搜索库"""
        # 定义要读取的文件名
        files = [
            "2001-2020.xlsx", "2021-2024.xlsx",
            "2001-2020.xlsx - Sheet1.csv", "2021-2024.xlsx - Sheet1.csv"
        ]
        
        # 临时存储去重后的股票信息
        unique_stocks = {}

        for f in files:
            path = os.path.join(self.data_dir, f)
            if not os.path.exists(path):
                continue
                
            try:
                # 读取数据 (强制转为字符串，防止代码前导0丢失)
                if f.endswith('.csv'):
                    df = pd.read_csv(path, dtype=str)
                else:
                    df = pd.read_excel(path, dtype=str)
                
                # 清洗列名 (去除空格)
                df.columns = [str(c).strip() for c in df.columns]
                
                # 智能识别列名
                col_map = {}
                for c in df.columns:
                    if '代码' in c: col_map['code'] = c
                    elif '简称' in c or '名称' in c: col_map['name'] = c
                    elif '年份' in c: col_map['year'] = c
                    elif '链接' in c or 'url' in c.lower(): col_map['url'] = c
                
                if 'code' in col_map and 'url' in col_map:
                    for _, row in df.iterrows():
                        # 处理代码
                        raw_code = str(row[col_map['code']])
                        if '.' in raw_code: raw_code = raw_code.split('.')[0]
                        code = raw_code.zfill(6)
                        
                        # 处理年份
                        raw_year = str(row[col_map['year']])
                        if '.' in raw_year: raw_year = raw_year.split('.')[0]
                        year = raw_year
                        
                        url = str(row[col_map['url']])
                        
                        # 处理名称
                        name = code # 默认用代码
                        if 'name' in col_map:
                            name = str(row[col_map['name']]).strip()
                        
                        # 1. 构建 URL 映射
                        key = f"{code}_{year}"
                        self.stock_map[key] = url
                        
                        # 2. 记录该股票的年份
                        if year and year.lower() != 'nan':
                            self.stock_years[code].add(year)

                        # 3. 构建搜索数据库 (去重)
                        if code not in unique_stocks:
                            unique_stocks[code] = name
                        else:
                            # 如果已有，优先保留较长的名称（有时候会有空简称）
                            if len(name) > len(unique_stocks[code]):
                                unique_stocks[code] = name
                                
            except Exception as e:
                print(f"Error loading {f}: {e}")

        # 将去重后的股票信息转为列表，供搜索使用
        self.stock_db = [{'code': k, 'name': v} for k, v in unique_stocks.items()]
        print(f"✅ ExcelReader 初始化完成: 加载了 {len(self.stock_db)} 只股票信息")

    def find_report_url(self, stock_code, year):
        """根据 6位代码 和 年份 查找 PDF 链接"""
        key = f"{str(stock_code).zfill(6)}_{str(year)}"
        return self.stock_map.get(key)

    def get_years(self, stock_code):
        """获取指定股票代码的所有可用年份，并排序"""
        stock_code = str(stock_code).zfill(6)
        years = list(self.stock_years.get(stock_code, []))
        # 尝试转数字排序，如果失败则按字符串排序
        try:
            years.sort(key=lambda x: int(x), reverse=True) # 降序，最近的年份在前
        except:
            years.sort(reverse=True)
        return years

    def search_stocks(self, query, limit=10):
        """模糊搜索股票"""
        if not query:
            return []
            
        query = str(query).lower().strip()
        results = []
        
        for stock in self.stock_db:
            code = stock['code']
            name = stock['name'].lower()
            
            if query in code or query in name:
                results.append(stock)
                
            if len(results) >= limit:
                break
                
        return results