import schedule
import time
import subprocess
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vector_db_update.log'),
        logging.StreamHandler()
    ]
)

def update_vector_db():
    """更新向量数据库的函数"""
    try:
        logging.info("Starting vector database update...")
        
        # 记录开始时间
        start_time = datetime.now()
        
        # 运行build_vectordb.py脚本
        result = subprocess.run(
            ['python', 'build_vectordb.py'],
            capture_output=True,
            text=True
        )
        
        # 记录结束时间和执行结果
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result.returncode == 0:
            logging.info(f"Vector database update completed successfully in {duration}")
            logging.info(f"Output: {result.stdout}")
        else:
            logging.error(f"Vector database update failed after {duration}")
            logging.error(f"Error: {result.stderr}")
            
    except Exception as e:
        logging.error(f"Error during vector database update: {str(e)}")

def main():
    """主函数，设置定时任务"""
    # 设置每周一凌晨2点运行更新
    schedule.every().monday.at("02:00").do(update_vector_db)
    
    # 立即运行一次（用于测试）
    logging.info("Running initial vector database update...")
    update_vector_db()
    
    logging.info("Scheduler started. Next update scheduled for next Monday at 02:00")
    
    # 保持脚本运行
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

if __name__ == "__main__":
    main() 