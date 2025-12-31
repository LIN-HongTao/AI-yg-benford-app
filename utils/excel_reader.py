import pandas as pd
from typing import Optional, Tuple
import os
import sys

class ExcelReader:
    def __init__(self):
        self.old_data = None
        self.new_data = None
        self._load_data()
        
    def resource_path(self, relative_path: str):
        """ 获取打包后资源的绝对路径 """
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(relative_path)
        return os.path.join(os.path.abspath("."), relative_path)
    
    def _load_data(self) -> None:
        """加载Excel数据"""
        # base_path = "A股年报链接大全"
        # old_file = os.path.join(base_path, "2001-2020.xlsx")
        # new_file = os.path.join(base_path, "2021-2024.xlsx")
        old_file = self.resource_path("2001-2020.xlsx")
        new_file = self.resource_path("2021-2024.xlsx")
        
        self.old_data = pd.read_excel(old_file)
        self.new_data = pd.read_excel(new_file)
    
    def find_report_url(self, stock_code: str, year: int) -> Optional[str]:
        """
        根据股票代码和年份查找年报PDF链接
        
        Args:
            stock_code: 股票代码（如：000001）
            year: 年份（如：2023）
            
        Returns:
            年报PDF链接，如果未找到则返回None
        """
        # 根据年份选择数据集
        data = self.new_data if year >= 2021 else self.old_data
        
        # 查找匹配的记录
        mask = (data['公司代码'] == int(stock_code)) & (data['年份'] == year)
        result = data[mask]
        
        if len(result) > 0:
            return result.iloc[-1]['年报链接']
        return None 