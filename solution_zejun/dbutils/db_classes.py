from tinydb import TinyDB, Query
from datetime import datetime as dt, timedelta
import os
from typing import List, Tuple, Optional, Dict, Any
import time


class ChartDB:
    def __init__(self, json_file_path: str):
        self.json_file_path = json_file_path
        self.db = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Check if DB exists, create with example record if not."""
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(self.json_file_path), exist_ok=True)
        # Initialize database
        self.db = TinyDB(self.json_file_path)
        # Check if database is empty and add example record
        if not self.db.all():
            example_record = {
                "ticker": "mock_ticker",
                "org": "zzj_org",
                "time_created": "2018-12-23 23:12:11",
                "url_keys": ["any", "thing", "url", "ids"]
            }
            self.db.insert(example_record)
            print(f"Created new database with example record at {self.json_file_path}")
    
    def insert_record(self, ticker: str, url_keys: List[str], org):
        """
        Insert a new record with current UTC timestamp.
        
        Args:
            ticker: Ticker symbol
            url_keys: List of URL keys
            
        Returns:
            Document ID of the inserted record
        """
        record = {
            "ticker": ticker,
            "org": org,
            "time_created": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "url_keys": url_keys
        }
        doc_id = self.db.insert(record)
        print(f"Inserted record for {ticker} with {len(url_keys)} URL keys")
        return doc_id
    
    def fetch_records(self, ticker: str) -> Tuple[Optional[List[str]], Optional[str], bool]:
        """
        Fetch records for a ticker and check if latest record is expired.
        
        Args:
            ticker: Ticker symbol to search for
            
        Returns:
            Tuple of (url_keys, time_created, expired)
            Returns (None, None, True) if no records found
        """
        Record = Query()
        records = self.db.search(Record.ticker == ticker)
        
        if not records:
            return None, None, True, None
        
        # Find the latest record by time_created
        records_with_dt = []
        for record in records:
            record_copy = record.copy()
            record_copy['dt'] = dt.strptime(record['time_created'], "%Y-%m-%d %H:%M:%S")
            records_with_dt.append(record_copy)

        latest_record = max(records_with_dt, key=lambda x: x['dt'])
        
        url_keys = latest_record['url_keys']
        time_created_str = latest_record['time_created']
        org = latest_record['org']
        
        # Check if record is older than 24 hours
        time_created = dt.strptime(time_created_str, "%Y-%m-%d %H:%M:%S")
        time_now = dt.utcnow()
        time_diff = time_now - time_created
        expired = time_diff > timedelta(hours=24)
        
        return url_keys, time_created_str, expired, org
    
    def check_latest(self, ticker: str) -> Tuple[Optional[List[str]], Optional[str], bool]:
        """
        Check the latest record for a ticker (combines check_db and fetch_records).
        
        Args:
            ticker: Ticker symbol to check
            
        Returns:
            Tuple of (url_keys, time_created, expired)
        """
        # Ensure DB is initialized
        self._initialize_db()
        
        # Fetch and check records
        return self.fetch_records(ticker)
    
    def get_all_records(self, ticker: str = None) -> List[Dict[str, Any]]:
        """
        Get all records, optionally filtered by ticker.
        
        Args:
            ticker: Optional ticker symbol to filter by
            
        Returns:
            List of all matching records
        """
        if ticker:
            Record = Query()
            return self.db.search(Record.ticker == ticker)
        return self.db.all()
    
    
# class JobRegisterMg:
#     def __init__(self, db_path: str):
#         """
#         Initialize Job Status Manager with TinyDB.
        
#         Args:
#             db_path: Path to the JSON database file (e.g., "data/job_status.json")
#         """
#         self.db_path = db_path
#         self.db = None
#         self._check_db()
    
#     def _check_db(self):
#         """Check if DB exists, create with example record if not."""
#         # Create directory if needed
#         directory = os.path.dirname(self.db_path)
#         if directory:  # Only if directory path is not empty
#             os.makedirs(directory, exist_ok=True)
        
#         # Initialize database
#         self.db = TinyDB(self.db_path)
        
#         # Check if database is empty and add example record
#         if not self.db.all():
#             example_record = {
#                 "job_id": "example_job_123",
#                 "status": "download started",
#                 "time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
#             }
#             self.db.insert(example_record)
#             print(f"Created new job status database with example record at {self.db_path}")
    
# #     def push_status(self, job_id: str, status: str) -> int:
# #         """
# #         Push a new job status record with current timestamp.
        
# #         Args:
# #             job_id: Job identifier
# #             status: Status message (e.g., "started", "completed", "failed")
            
# #         Returns:
# #             Document ID of the inserted record
# #         """
# #         record = {
# #             "job_id": job_id,
# #             "status": status,
# #             "time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
# #         }
# #         doc_id = self.db.insert(record)
# #         print(f"Job {job_id}: {status}")
# #         return doc_id
    
#     def get_next_id(self):
#         """Get the next available ID by finding the maximum existing ID."""
#         all_docs = self.db.all()
#         if not all_docs:
#             return 1

#         # Get all document IDs
#         existing_ids = [doc.doc_id for doc in all_docs]
#         return max(existing_ids) + 1

#     def push_status(self, job_id: str, status: str):
#         """Insert with ID detection and retry logic."""
#         record = {
#             "job_id": job_id,
#             "status": status,
#             "time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
#         }
#         for attempt in range(3):
#             try:
                
#                 next_id = self.get_next_id()
#                 doc_id = self.db.insert(record, doc_id=next_id)
#                 return doc_id
            
#             except ValueError as e:
#                 if "already exists" in str(e):
#                     time.sleep(0.1 * (attempt + 1))
#                     continue
#                 raise
#         raise Exception("Failed to insert after retries")

#     def get_job_status(self, job_id: str) -> str:
#         """
#         Get the latest status for a job by job_id.
        
#         Args:
#             job_id: Job identifier to search for
            
#         Returns:
#             Latest status message or "nothing" if no records found
#         """
#         Job = Query()
#         records = self.db.search(Job.job_id == job_id)
        
#         if not records:
#             return "nothing"
        
#         # Find the latest record by time (convert string to datetime for proper comparison)
#         latest_record = max(records, key=lambda x: dt.strptime(x['time'], "%Y-%m-%d %H:%M:%S"))
#         return latest_record['status']
    
#     def get_job_history(self, job_id: str) -> list:
#         """
#         Get all status records for a job, sorted by time.
        
#         Args:
#             job_id: Job identifier
            
#         Returns:
#             List of all status records for the job, sorted by time (newest first)
#         """
#         Job = Query()
#         records = self.db.search(Job.job_id == job_id)
        
#         # Sort by time descending (newest first)
#         records.sort(key=lambda x: dt.strptime(x['time'], "%Y-%m-%d %H:%M:%S"), reverse=True)
        
#         return records
    
#     def get_all_jobs(self) -> list:
#         """
#         Get list of all unique job IDs in the database.
        
#         Returns:
#             List of unique job IDs
#         """
#         all_records = self.db.all()
#         job_ids = set(record['job_id'] for record in all_records)
#         return list(job_ids)
    
#     def get_latest_status_all_jobs(self) -> Dict[str, str]:
#         """
#         Get the latest status for all jobs.
        
#         Returns:
#             Dictionary with job_id as key and latest status as value
#         """
#         results = {}
#         for job_id in self.get_all_jobs():
#             results[job_id] = self.get_job_status(job_id)
#         return results
    

class NewsManager:
    def __init__(self, db_path: str):
        """
        Initialize News Manager with TinyDB.
        
        Args:
            db_path: Path to the JSON database file (e.g., "data/news_db.json")
        """
        self.db_path = db_path
        self.db = None
        self._check_db()
    
    def _check_db(self):
        """Check if DB exists, create with example record if not."""
        # Create directory if needed
        directory = os.path.dirname(self.db_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize database
        self.db = TinyDB(self.db_path)
        
        # Check if database is empty and add example record
        if not self.db.all():
            example_record = {
                "url": "https://example.com/news/article1",
                "title": "Example News Article",
                "file_path": "/path/to/example/file.html",
                "create_time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "content": "pending",
                "summary": "pending",
                "publish_date": ""
            }
            self.db.insert(example_record)
            print(f"Created new news database with example record at {self.db_path}")
    
    def push_record_initial(self, url: str, title: str, file_path: str = "") -> int:
        """
        Push a new news record.
        
        Args:
            url: News article URL
            title: Article title
            file_path: Path to downloaded file (optional)
            
        Returns:
            Document ID of the inserted record
        """
        record = {
            "url": url,
            "title": title,
            "file_path": file_path,
            "create_time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "content": "pending",
            "summary": "pending",
            "publish_date": ""
        }
        doc_id = self.db.insert(record)
        print(f"Added news record: {title}")
        return doc_id
    
    def fetch_records(self, urls: List[str]) -> Dict[str, Optional[Dict]]:
        """
        Fetch records for a list of URLs.
        
        Args:
            urls: List of URLs to search for
            
        Returns:
            Dictionary with URLs as keys and records as values (None if not found)
        """
        News = Query()
        results = {}
        
        for url in urls:
            records = self.db.search(News.url == url)
            if records:
                results[url] = records[0] # always unique
            else:
                results[url] = None
        
        return results
    
    def update_fields(self, url: str, **updates) -> bool:
        """
        Update fields for a record matching the URL.
        
        Args:
            url: URL to match for update
            **updates: Fields to update (e.g., content="new content", summary="new summary")
            
        Returns:
            True if record was updated, False if not found
        """
        News = Query()
        records = self.db.search(News.url == url)
        
        if not records:
            print(f"No record found for URL: {url}")
            return False
        
        # Update all matching records (usually should be only one)
        self.db.update(updates, News.url == url)
        print(f"Updated record for {url}: {list(updates.keys())}")
        return True
    
    def get_all_urls(self) -> List[str]:
        """
        Get all unique URLs in the database.
        
        Returns:
            List of unique URLs
        """
        all_records = self.db.all()
        urls = list(set(record['url'] for record in all_records))
        return urls
    
    def get_record_by_url(self, url: str) -> Optional[Dict]:
        """
        Get the most recent record for a specific URL.
        
        Args:
            url: URL to search for
            
        Returns:
            Record dictionary or None if not found
        """
        News = Query()
        records = self.db.search(News.url == url)
        
        if not records:
            return None
        
        # Return the most recent record
        return max(records, key=lambda x: dt.strptime(x['create_time'], "%Y-%m-%d %H:%M:%S"))
    
    
    
class NewsCropDatabase:
    def __init__(self, json_file_path: str):
        """
        Initialize News Crop Database with TinyDB.
        
        Args:
            json_file_path: Path to the JSON database file
        """
        self.json_file_path = json_file_path
        self.db = None
        self._check_db()
    
    def _check_db(self):
        """Check if DB exists, create with example record if not."""
        # Create directory if needed
        directory = os.path.dirname(self.json_file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        
        # Initialize database
        self.db = TinyDB(self.json_file_path)
        
        # Check if database is empty and add example record
        if not self.db.all():
            example_rcd = {
                "org": "mock_company",
                "ticker": "mock.HK",
                "url": "https://example.com/hsbc-news",
                "time_created": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                "related_reason_simple": "Earnings report",
                "related_reason_short": "Q3 earnings beat",
                "polarity": "positive",
                "title": "HSBC Q3 Earnings Exceed Expectations",
                "actual_trend": "up",
                "quote_frag": "HSBC reported 12% profit growth"
            }
            self.db.insert(example_rcd)
            print(f"Created new news crop database with example record at {self.json_file_path}")
    
    def insert_record(self, record_data: Dict) -> int:
        """
        Insert a new record into the database.
        
        Args:
            record_data: Dictionary containing record fields
            
        Returns:
            Document ID of the inserted record
        """
        # Ensure required fields are present
        if 'time_created' not in record_data:
            record_data['time_created'] = dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
        doc_id = self.db.insert(record_data)
        print(f"Inserted record for {record_data.get('ticker', 'unknown')} - {record_data.get('title', 'no title')}")
        return doc_id
    
    def fetch_records(self, ticker: str, limit: int = 10) -> List[Dict]:
        """
        Fetch records for a specific ticker, return top N most recent.
        
        Args:
            ticker: Ticker symbol to search for
            limit: Maximum number of records to return
            
        Returns:
            List of records sorted by time_created (newest first)
        """
        News = Query()
        records = self.db.search(News.ticker == ticker)
        
        if not records:
            return []
        
        # Sort by time_created descending (newest first)
        records.sort(key=lambda x: dt.strptime(x['time_created'], "%Y-%m-%d %H:%M:%S"), reverse=True)
        
        return records[:limit]
    
    def check_fragments(self, url: str, ticker: str) -> bool:
        """
        Check if a record already exists for the given URL and ticker.
        
        Args:
            url: URL to check
            ticker: Ticker symbol to check
            
        Returns:
            True if record exists, False otherwise
        """
        News = Query()
        records = self.db.search((News.url == url) & (News.ticker == ticker))
        return len(records) > 0
