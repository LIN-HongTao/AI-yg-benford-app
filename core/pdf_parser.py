import pdfplumber
import pandas as pd
from typing import List, Tuple, Any, Optional
import re
from pathlib import Path
import warnings
# 忽略PDF解析警告
warnings.filterwarnings("ignore")

class PDFParser:
    def __init__(self):
        self.table_start_markers = [
            "合并资产负债表",
            "合并利润表",
            "合并现金流量表"
        ]
        self.table_end_markers = [
            "合并所有者权益变动表",
            "母公司所有者权益变动表"
        ]
        
    def find_page_range(self, pdf: Any, start_keyword: str, end_keyword: str) -> Tuple[int | None, int | None]:
        """查找起止关键词所在页码区间（起始包含，终止不包含）"""
        pre_page: int | None = None
        start_page: int | None = None
        end_page: int | None = None
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if pre_page is None and "财务报表" in text:
                pre_page = i
            if pre_page is not None and start_page is None and start_keyword in text and ("财务报表" in text or "项目" in text):
                start_page = i
                continue
            if start_page is not None and end_keyword in text:
                end_page = i
                break
        print("start_page", start_page, "end_page", end_page)
        return start_page, end_page

    def extract_tables(self, pdf_path: str) -> pd.DataFrame:
        """提取PDF中指定页码区间内的所有表格并合并"""
        all_data = []
        with pdfplumber.open(Path(pdf_path)) as pdf:
            start_page, end_page = self.find_page_range(pdf, "合并资产负债表", "合并所有者权益变动表")
            if start_page is None or end_page is None:
                print("未找到指定区间！")
                return pd.DataFrame()
                
            for i in range(start_page, end_page):
                page = pdf.pages[i]
                for table in page.extract_tables():
                    if table and len(table) > 1:  # 确保表格至少包含表头和一行数据           
                        
                        # 如果列数为9列，处理表格
                        # 修复表头，将“期末余额”和“期初余额”左移一列
                        header = table[0]
                        if len(header) == 9:
                            header_fixed = header[:]
                            header_fixed[3] = header_fixed[4]
                            header_fixed[4] = ''
                            header_fixed[6] = header_fixed[7]
                            header_fixed[7] = ''
                            # for i in range(1, len(header)):
                            #     if header[i] == '期末余额':
                            #         header_fixed[i-1] = '期末余额'
                            #         header_fixed[i] = ''
                            #     elif header[i] == '期初余额':
                            #         header_fixed[i-1] = '期初余额'
                            #         header_fixed[i] = ''
                            table[0] = header_fixed
                        
                        # 清理表格数据
                        cleaned_table = []
                        for row in table:
                            cleaned_row = [self._clean_cell(cell) for cell in row]
                            if any(cleaned_row):  # 只保留非空行
                                cleaned_table.append(cleaned_row)
                        
                        if len(cleaned_table) > 1:  # 确保清理后仍然有数据
                            # 检查列数是否一致
                            if not all(len(row) == len(cleaned_table[0]) for row in cleaned_table):
                                # 如果列数不一致，取最长的行作为标准
                                max_cols = max(len(row) for row in cleaned_table)
                                # 对每行进行填充或截断
                                cleaned_table = [
                                    row + [''] * (max_cols - len(row)) if len(row) < max_cols
                                    else row[:max_cols]
                                    for row in cleaned_table
                                ]
                            all_data.extend(cleaned_table)
        
        if not all_data:
            return pd.DataFrame()
        try:
            # 使用第一行作为列名，其余行作为数据
            headers = all_data[0]
            data = all_data[1:]
            
            # 确保所有行的列数与表头一致
            data = [
                row + [''] * (len(headers) - len(row)) if len(row) < len(headers)
                else row[:len(headers)]
                for row in data
            ]
            
            # 创建DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # 清理列名
            df.columns = [self._clean_cell(col) for col in df.columns]
            
            # 删除全为空的行和列
            df = df.dropna(how='all').dropna(axis=1, how='all')

            # 尝试将数值列转换为数值类型
            for col in df.columns:
                # 跳过包含非数值字符的列名
                if any(char in col for char in ['项目', '附注']):
                    continue
                    
                try:
                    # 清理数值数据
                    df[col] = df[col].apply(self._convert_to_numeric)
                except:
                    continue
            return df
        except Exception as e:
            print(f"创建DataFrame时出错: {str(e)}")
            return pd.DataFrame()
    
    def _clean_cell(self, cell: Optional[str]) -> str:
        """
        清理单元格数据
        
        Args:
            cell: 原始单元格数据
            
        Returns:
            清理后的数据
        """
        if not cell:
            return ""
        
        # 移除特殊字符和多余空格
        cell = re.sub(r'[^\w\s\u4e00-\u9fff\-\.]', '', str(cell))
        cell = re.sub(r'\s+', ' ', cell).strip()
        
        return cell
    
    def _convert_to_numeric(self, value: str) -> float:
        """
        将字符串转换为数值
        
        Args:
            value: 输入字符串
            
        Returns:
            转换后的数值
        """
        if not value:
            return 0.0
            
        # 移除所有非数字字符（保留小数点和负号）
        value = re.sub(r'[^\d\-\.]', '', str(value))
        
        try:
            return float(value)
        except:
            return 0.0 