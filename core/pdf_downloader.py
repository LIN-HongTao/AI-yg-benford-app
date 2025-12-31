import requests
import os
from typing import Optional
from pathlib import Path

class PDFDownloader:
    def __init__(self, save_dir: str = "reports"):
        self.save_dir = save_dir
        Path(save_dir).mkdir(exist_ok=True)
    
    def download_pdf(self, url: str, stock_code: str, year: int) -> Optional[str]:
        """
        下载PDF文件
        
        Args:
            url: PDF文件URL
            stock_code: 股票代码
            year: 年份
            
        Returns:
            下载文件的路径，如果下载失败则返回None
        """
        try:
            # 构建保存路径
            filename = f"{stock_code}_{year}_annual_report.pdf"
            save_path = os.path.join(self.save_dir, filename)
            
            # 下载文件
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # 保存文件
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            return save_path
            
        except Exception as e:
            print(f"下载失败: {str(e)}")
            return None 