import math
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List, Any
from scipy import stats
import re

class BenfordAnalyzer:
    def __init__(self):
        self._distribution_cache: Dict[Tuple[int, int], Dict[int, float]] = {}

    def analyze(
        self,
        df: pd.DataFrame,
        digit_position: int = 1,
        numeral_system: str = 'decimal'
    ) -> Tuple[Dict[str, float], float, Dict[str, int], str, Dict[str, Any], List[Dict]]:
        
        base_map = {'decimal': 10, 'octal': 8, 'hexadecimal': 16}
        if numeral_system not in base_map:
            raise ValueError("不支持的进制体系")
        base = base_map[numeral_system]

        numbers, records = self._extract_valid_numbers_with_details(df)
        
        empty_metadata = {
            'base': base, 'digit_position': digit_position, 
            'sample_size': 0, 'degrees_of_freedom': 0, 
            'p_value': 1.0, 'critical_value_95': 0.0, 'theoretical_distribution': {}
        }

        if len(numbers) < 10:
             return {}, 0.0, {}, "样本数量过少 (<10)，无法进行有效分析。", empty_metadata, []

        theoretical_dist = self._get_theoretical_distribution(base, digit_position)
        
        counts = {k: 0 for k in theoretical_dist.keys()}
        valid_sample_count = 0
        enriched_records = [] 
        
        for i, num in enumerate(numbers):
            digit = self._get_digit_at_position(num, base, digit_position)
            rec = records[i]
            
            if digit is not None and digit in counts:
                counts[digit] += 1
                valid_sample_count += 1
                rec['extracted_digit'] = self._format_digit(digit, base)
                enriched_records.append(rec)
        
        if valid_sample_count == 0:
            return {}, 0.0, {}, "未提取到有效位数的数字", empty_metadata, []

        actual_dist = {k: v / valid_sample_count for k, v in counts.items()}

        chi_square = 0.0
        for d_int, prob in theoretical_dist.items():
            obs = counts.get(d_int, 0)
            exp = prob * valid_sample_count
            if exp > 0:
                chi_square += (obs - exp) ** 2 / exp

        degrees_of_freedom = len(theoretical_dist) - 1
        p_value = stats.chi2.sf(chi_square, degrees_of_freedom)
        critical_value_95 = stats.chi2.ppf(0.95, degrees_of_freedom)

        def fmt(d): return self._format_digit(d, base)
        
        final_actual_dist = {fmt(k): v for k, v in actual_dist.items()}
        final_counts = {fmt(k): v for k, v in counts.items()}
        final_theo_dist = {fmt(k): v for k, v in theoretical_dist.items()}

        conclusion = self._generate_dynamic_conclusion(
            chi_square, p_value, valid_sample_count, numeral_system
        )

        metadata = {
            'base': base,
            'digit_position': digit_position,
            'sample_size': valid_sample_count,
            'degrees_of_freedom': degrees_of_freedom,
            'p_value': p_value,
            'critical_value_95': critical_value_95,
            'theoretical_distribution': final_theo_dist
        }

        return final_actual_dist, chi_square, final_counts, conclusion, metadata, enriched_records

    def _extract_valid_numbers_with_details(self, df: pd.DataFrame) -> Tuple[List[float], List[Dict]]:
        """
        提取数字并记录来源详情
        【升级】：增加 row_label (项目名称) 的提取
        """
        values = []
        records = []
        
        ignore_keywords = ['附注', 'note', '注释', '行次'] # 移除了 '项目'，因为我们要用它
        number_pattern = re.compile(r'^-?\d+(\.\d+)?$')

        # --- 1. 寻找“项目名称”列 ---
        # 逻辑：优先找包含 "项目"、"Item" 的列，如果找不到，就默认第一列是标签列
        label_col = None
        for col in df.columns:
            c_str = str(col).lower()
            if '项目' in c_str or 'item' in c_str:
                label_col = col
                break
        
        if label_col is None and len(df.columns) > 0:
            label_col = df.columns[0] # 降级策略：默认第一列

        # --- 内部函数：智能日期判断 ---
        def is_date_like(val_float: float) -> bool:
            if not val_float.is_integer(): return False
            s = str(int(val_float))
            if len(s) != 8: return False
            year = int(s[0:4])
            if not (1990 <= year <= 2030): return False
            month = int(s[4:6])
            if not (1 <= month <= 12): return False
            day = int(s[6:8])
            if not (1 <= day <= 31): return False
            return True

        for col in df.columns:
            col_clean = str(col).lower().replace(' ', '').replace('\n', '')
            if not col_clean: continue
            
            # 如果这一列就是“项目名称”列，或者是忽略列，跳过
            if col == label_col: continue 
            if any(keyword in col_clean for keyword in ignore_keywords): continue

            for idx, item in df[col].items():
                if pd.isna(item): continue
                
                s = str(item).strip().replace(',', '')
                
                if number_pattern.fullmatch(s):
                    try:
                        val = float(s)
                        if val == 0: continue
                        if val.is_integer() and 1990 <= val <= 2030: continue
                        if is_date_like(val): continue
                        
                        val_abs = abs(val)
                        values.append(val_abs)
                        
                        # --- 获取当前行的“项目名称” ---
                        row_label_text = "N/A"
                        if label_col is not None:
                            try:
                                # 获取标签列在当前行 (idx) 的值
                                label_val = df.at[idx, label_col]
                                if pd.notna(label_val):
                                    row_label_text = str(label_val).strip().replace('\n', ' ')
                            except:
                                pass

                        records.append({
                            'row_label': row_label_text, # 新增：项目名称 (如 "货币资金")
                            'column_name': str(col),     # 列名 (如 "2023年12月31日")
                            'original_text': str(item),
                            'extracted_value': val_abs,
                            'row_index': idx
                        })
                    except ValueError:
                        continue
                        
        return values, records

    # ... (其余方法保持不变: _get_digit_at_position, _get_theoretical_distribution, _format_digit, _generate_dynamic_conclusion) ...
    def _get_digit_at_position(self, num: float, base: int, position: int) -> int | None:
        if num <= 0: return None
        try:
            log_val = math.log(num, base)
            decimal_part = log_val - math.floor(log_val)
            normalized = base ** decimal_part
            shifted = normalized * (base ** (position - 1))
            digit = int(shifted) % base
            if position == 1 and digit == 0: return None
            return digit
        except: return None

    def _get_theoretical_distribution(self, base: int, position: int) -> Dict[int, float]:
        cache_key = (base, position)
        if hasattr(self, '_distribution_cache') and cache_key in self._distribution_cache:
            return self._distribution_cache[cache_key]
        dist = {}
        start_digit = 1 if position == 1 else 0
        for d in range(start_digit, base):
            prob = 0.0
            if position == 1: prob = math.log(1 + 1/d, base)
            elif position == 2: 
                for k in range(1, base): prob += math.log(1 + 1/(k * base + d), base)
            else: prob = 1.0 / base
            dist[d] = prob
        if not hasattr(self, '_distribution_cache'): self._distribution_cache = {}
        self._distribution_cache[cache_key] = dist
        return dist

    def _format_digit(self, digit: int, base: int) -> str:
        if digit < 10: return str(digit)
        return chr(ord('A') + digit - 10)

    def _generate_dynamic_conclusion(self, chi2: float, p_value: float, n: int, system: str) -> str:
        warning = ""
        if n < 50: warning = "⚠️ [警告] 样本量过少 (<50)，卡方检验统计效力不足，结果仅供参考。\n"
        if p_value < 0.01:
            risk = "高风险 (严重偏离)"
            desc = f"数据分布与本福特理论分布存在极显著差异 (P < 0.01)。这意味着该差异由随机因素导致的可能性极低 ({p_value:.4f})，高度怀疑数据存在异常或被人为干预，建议进行深入审计。"
        elif p_value < 0.05:
            risk = "中等风险 (显著偏离)"
            desc = f"数据分布与本福特理论分布存在显著差异 (0.01 ≤ P < 0.05)。虽然不如高风险极端，但仍表明数据可能偏离自然规律，建议核查数据质量或特定业务逻辑。"
        else:
            risk = "低风险 (符合预期)"
            desc = f"数据分布与本福特理论分布没有显著差异 (P > 0.05)。未能拒绝原假设，数据表现符合自然规律，未发现明显异常。"
        return f"""{warning}
分析体系：{system}
结论等级：{risk}
{desc}"""