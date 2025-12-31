import os
import sys
import uuid
from flask import Flask, render_template, request, jsonify

# 确保能导入本地模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.pdf_downloader import PDFDownloader
from core.pdf_parser import PDFParser
from core.benford_analyzer import BenfordAnalyzer
from utils.excel_reader import ExcelReader

app = Flask(__name__)

# 初始化工具类
excel_reader = ExcelReader()
downloader = PDFDownloader(save_dir="temp_reports")
parser = PDFParser()
analyzer = BenfordAnalyzer()

@app.route('/')
def index():
    return render_template('index.html')

# === 股票搜索接口 ===
@app.route('/api/search', methods=['GET'])
def search_stock():
    """根据关键词搜索股票代码或简称"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'success': True, 'data': []})
    
    results = excel_reader.search_stocks(query)
    return jsonify({'success': True, 'data': results})

# === 新增：获取年份接口 ===
@app.route('/api/years', methods=['GET'])
def get_stock_years():
    """根据股票代码获取可用年份"""
    code = request.args.get('code', '').strip()
    if not code:
        return jsonify({'success': False, 'data': []})
    
    years = excel_reader.get_years(code)
    return jsonify({'success': True, 'data': years})
# ========================

@app.route('/api/analyze', methods=['POST'])
def analyze():
    pdf_path = None
    
    try:
        # === 1. 参数获取与文件来源判断 ===
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({'success': False, 'message': '未选择文件'}), 400
            
            digit_position = int(request.form.get('digit_position', 1))
            numeral_system = request.form.get('numeral_system', 'decimal')
            
            temp_filename = f"upload_{uuid.uuid4().hex}.pdf"
            pdf_path = os.path.join("temp_reports", temp_filename)
            file.save(pdf_path)
            
            stock_code = "MANUAL_UPLOAD"
            year = "N/A"
            
        else:
            data = request.json
            stock_code = data.get('stock_code') 
            year = str(data.get('year')) # 确保是字符串
            digit_position = int(data.get('digit_position', 1))
            numeral_system = data.get('numeral_system', 'decimal')

            pdf_url = excel_reader.find_report_url(stock_code, year)
            if not pdf_url:
                return jsonify({'success': False, 'message': f'未找到 {stock_code} {year} 年的年报链接，请确认年份或代码是否在数据库中'}), 404

            pdf_path = downloader.download_pdf(pdf_url, stock_code, year)
            if not pdf_path:
                return jsonify({'success': False, 'message': 'PDF 下载失败，请稍后重试'}), 500

        # === 2. 核心分析流程 ===
        try:
            df = parser.extract_tables(pdf_path)
            
            if df.empty:
                return jsonify({'success': False, 'message': '该年报财务表格格式不标准，暂时未能从 PDF 中提取到有效的财务表格'}), 400

            actual, chi_square, counts, conclusion, metadata, raw_records = analyzer.analyze(
                df, 
                digit_position=digit_position, 
                numeral_system=numeral_system
            )

            def sort_key(k):
                if k.isdigit(): return int(k)
                return 10 + ord(k.upper()) - ord('A')
            
            sorted_keys = sorted(list(actual.keys()), key=sort_key)
            theo_dist = metadata.get('theoretical_distribution', {})

            result_data = {
                'labels': sorted_keys,
                'actual_freq': [actual[k] for k in sorted_keys],
                'theoretical_freq': [theo_dist.get(k, 0) for k in sorted_keys],
                'counts': [counts[k] for k in sorted_keys],
                'chi_square': round(chi_square, 2),
                'p_value': f"{metadata['p_value']:.4f}",
                'critical_value': round(metadata['critical_value_95'], 2),
                'degrees_of_freedom': metadata['degrees_of_freedom'],
                'conclusion': conclusion,
                'metadata': {
                    'stock_code': stock_code,
                    'year': year,
                    'sample_size': metadata['sample_size'],
                    'numeral_system': numeral_system
                },
                'raw_data': raw_records
            }
            
            return jsonify({'success': True, 'data': result_data})

        finally:
            if pdf_path and os.path.exists(pdf_path):
                try:
                    os.remove(pdf_path)
                except:
                    pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    if not os.path.exists("temp_reports"):
        os.makedirs("temp_reports")
    
    print("启动服务: http://0.0.0.0:5000")
    app.run(debug=False, host='0.0.0.0', port=5000)