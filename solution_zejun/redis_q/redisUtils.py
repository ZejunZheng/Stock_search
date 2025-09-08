import redis
import json
from datetime import datetime as dt

        
class RQJobQ:
    def __init__(self, host = 'localhost', port = 6379, dbId = 0, decode_rsp=True):
        self.RQ = redis.Redis(
            host=host,
            port=port,
            db=dbId,
            decode_responses=decode_rsp
        )
        self.crawl_queue_name = "news_job_queue"
        self.sumary_queue_name = "summary_job_queue"
        self.crop_queue_name = "corp_job_queue"
    
    def push_crawler_job(self, job_id, ticker):

        job_data = {
            'job_id': job_id,
            'data': ticker
        }
        self.RQ.rpush(self.crawl_queue_name, json.dumps(job_data))
        print(f"Produced crawler job {job_id} for ticker: {ticker}")
        return job_id
    
    def get_crawler_job(self):
        _, job_json = self.RQ.blpop(self.crawl_queue_name, timeout=30)
        print(job_json)

        if job_json:
            job_data = json.loads(job_json)
            job_id = job_data['job_id']
            ticker = job_data['data']
        return job_id, ticker
    
    def push_summary_job(self, job_id, urls, ticker, org):

        job_data = {
            'job_id': job_id,
            'data': urls,
            "ticker": ticker, 
            "org": org
        }
        self.RQ.rpush(self.sumary_queue_name, json.dumps(job_data))
        print(f"Produced summary job {job_id} for urls: n = {len(urls)}")
        return job_id
    
    def get_summary_job(self):
        _, job_json = self.RQ.blpop(self.sumary_queue_name, timeout=30)
        print(job_json)

        if job_json:
            job_data = json.loads(job_json)
            job_id = job_data['job_id']
            urls = job_data['data']
            ticker = job_data["ticker"] 
            org = job_data["org"]
        return job_id, urls, ticker, org
    
    def push_crop_job(self, job_id, urls, ticker, org):

        job_data = {
            'job_id': job_id,
            'data': urls,
            "ticker": ticker, 
            "org": org
        }
        self.RQ.rpush(self.crop_queue_name, json.dumps(job_data))
        print(f"Produced cropping job {job_id} for urls: n = {len(urls)}")
        return job_id
    
    def get_crop_job(self):
        _, job_json = self.RQ.blpop(self.crop_queue_name, timeout=30)
        print(job_json)

        if job_json:
            job_data = json.loads(job_json)
            job_id = job_data['job_id']
            urls = job_data['data']
            ticker = job_data["ticker"]
            org = job_data["org"]
        return job_id, urls, ticker, org
    
    
class JobRegisterMg:
    def __init__(self, host='localhost', port=6379, dbId=1, decode_rsp=True):
        self.JDB = redis.Redis(
            host=host,
            port=port,
            db=dbId,
            decode_responses=decode_rsp
        )
    
    def push_status(self, job_id: str, status: str):
        """Push job status to Redis using lists."""
        key = f"job:{job_id}:status"  # Redis key pattern
        
        record = {
            "job_id": job_id,
            "status": status,
            "time": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Push to Redis list (RPUSH for adding to end of list)
        self.JDB.rpush(key, json.dumps(record))
        print(f"Pushed status for job {job_id}: {status}")
    
    def get_job_status(self, job_id: str) -> str:
        """
        Get the latest status for a job from Redis.
        
        Args:
            job_id: Job identifier to search for
            
        Returns:
            Latest status message or "nothing" if no records found
        """
        key = f"job:{job_id}:status"
        
        # Get all status records for this job
        records_json = self.JDB.lrange(key, 0, -1)  # Get all items in list
        
        if not records_json:
            return "nothing"
        
        # Parse JSON records and find the latest one
        records = [json.loads(record) for record in records_json]
        latest_record = max(records, key=lambda x: dt.strptime(x['time'], "%Y-%m-%d %H:%M:%S"))
        status = [x['status'] for x in records]
        if "news crops ready" in status:
            return "news crops ready"
        
        return latest_record['status']
    
    def get_job_history(self, job_id: str) -> list:
        """Get all status records for a job, sorted by time."""
        key = f"job:{job_id}:status"
        records_json = self.JDB.lrange(key, 0, -1)
        
        if not records_json:
            return []
        
        records = [json.loads(record) for record in records_json]
        # Sort by time descending (newest first)
        records.sort(key=lambda x: dt.strptime(x['time'], "%Y-%m-%d %H:%M:%S"), reverse=True)
        
        return records
    
    def get_all_jobs(self) -> list:
        """Get list of all job IDs in the database."""
        # Get all keys that match the job status pattern
        keys = self.JDB.keys("job:*:status")
        # Extract job IDs from keys
        job_ids = [key.split(':')[1] for key in keys]
        return list(set(job_ids))  # Remove duplicates
    
    def clear_job_history(self, job_id: str) -> int:
        """Clear all status records for a job."""
        key = f"job:{job_id}:status"
        return self.JDB.delete(key)
    
    
    
