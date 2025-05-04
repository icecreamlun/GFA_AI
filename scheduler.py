import os
import subprocess
import logging
import time
import schedule
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def update_vector_db():
    """
    Update the vector database by running build_vectordb.py
    """
    try:
        # Record start time
        start_time = datetime.now()
        logger.info("Starting vector database update...")

        # Run build_vectordb.py script
        result = subprocess.run(
            ["python", "build_vectordb.py"],
            capture_output=True,
            text=True
        )

        # Record end time and execution result
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        if result.returncode == 0:
            logger.info(f"Vector database update completed successfully in {duration:.2f} seconds")
        else:
            logger.error(f"Vector database update failed after {duration:.2f} seconds")
            logger.error(f"Error output: {result.stderr}")

    except Exception as e:
        logger.error(f"Error during vector database update: {str(e)}")

def main():
    # Schedule weekly update (every Monday at 2:00 AM)
    schedule.every().monday.at("02:00").do(update_vector_db)

    # Run immediately once (for testing)
    update_vector_db()

    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    main() 