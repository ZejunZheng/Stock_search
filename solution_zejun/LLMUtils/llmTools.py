import os
import requests
from dotenv import load_dotenv
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import time
from datetime import datetime as dt
import json

import redis_q.redisUtils as rq
import dbutils.db_classes as dbs

class FinancialNewsSummarizor:
    def __init__(self, system_prompt_path: str, news_db_path: str, env_path: str):
        self.system_prompt_path = system_prompt_path
        self.news_db_path = news_db_path
        self.env_path = env_path
        
        # Initialize components
        self.sys_prompt = self._get_prompt()
        self.headers = self._set_headers()
        self.news_db = dbs.NewsManager(news_db_path)
        self.job_status = rq.JobRegisterMg()
        
    
    def _get_prompt(self) -> str:
        """Load system prompt from file."""
        try:
            with open(self.system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {self.system_prompt_path}")
        except Exception as e:
            raise RuntimeError(f"Error reading prompt file: {e}")

    def _set_headers(self) -> Dict[str, str]:
        """Set API headers."""
        load_dotenv(self.env_path)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
            
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
 
    def extract_news_content(self, url: str):
        record = self.news_db.get_record_by_url(url)
        
        if not record or record.get('file_path') in [None, "", "pending"]:
            return None
        
        with open(record.get('file_path'), 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, "html.parser")

        main = soup.find("main")
        if not main:
            return None
        
        # Get text content inside <main>, excluding scripts/styles
        for tag in main(["script", "style"]):
            tag.decompose()

        content = main.get_text(separator="\n", strip=True)
        lines = content.split("Story continues")[0].split("\n")
        new_content = ""
        for line in lines:
            if line.startswith(")") | (len(line) < 10) :
                new_content += " " + line
            else:
                new_content += "\n" + line

        return new_content
       
    def get_summary(self, content: str) -> Dict[str, str]:
        """
        Get summary and publication date from LLM API.
        
        Args:
            url: News article URL (for context)
            content: Article content to summarize
            
        Returns:
            Dictionary with summary and publication date
        """
        # Prepare user message
        user_msg = f"""
        
        Content: {content}
        
        Please provide a summary and infer the publication date.
        """
        
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user", "content": user_msg}
        ]
        
        payload = {
            "model": "gpt-5",  # or "gpt-3.5-turbo" depending on your access
            "messages": messages,
            #"temperature": 0.1  # Low temperature for more deterministic results
        }
        
        api_url = "https://api.openai.com/v1/chat/completions"
        
        try:
            response = requests.post(api_url, headers=self.headers, json=payload, timeout=40)
            # print(f"API ---: {response.status_code} {response.text}")
            if response.status_code != 200:
                raise RuntimeError(f"API call failed: {response.status_code} {response.text}")
            
            # Parse response
            result = response.json()
            # print(f" >> result {result}")
            llm_output = result['choices'][0]['message']['content']
            
            # Parse the LLM output to extract summary and date
            # This depends on your prompt structure - adjust accordingly
            summary = self._parse_summary(llm_output)
            publish_date = self._parse_date(llm_output)
            
            return {
                "summary": summary,
                "publish_date": publish_date if publish_date else ""
            }
            
        except requests.exceptions.Timeout:
            raise RuntimeError("API request timed out")
        except Exception as e:
            raise RuntimeError(f"Error calling LLM API: {e}")
    
    def _parse_summary(self, llm_output: str) -> str:
        """Parse summary from LLM output."""
        # Implement parsing logic based on your prompt structure
        # Example: if LLM returns "Summary: [text]\nDate: [date]"
        lines = llm_output.split('\n')
        for line in lines:
            if line.lower().startswith('summary:'):
                return line.split(':', 1)[1].strip()
        return llm_output  # Fallback: return entire output
    
    def _parse_date(self, llm_output: str) -> str:
        """Parse date from LLM output."""
        # Implement date parsing logic based on your prompt structure
        lines = llm_output.split('\n')
        for line in lines:
            if line.lower().startswith('date:'):
                date_str = line.split(':', 1)[1].strip()
                # Validate date format or convert if needed
                return date_str
        return ""
    
    def process_news_article(self, url: str) -> Dict[str, str]:
        print(f"Processing article: {url}")
        
        # Get content
        content = self.extract_news_content(url)
        if not content:
            return {"error": "Content not available"}
        print(f"content length: {len(content)}")
        
        # Get summary from LLM
        try:
            llm_result = self.get_summary(content)
        except Exception as e:
            return {"error": f"LLM processing failed: {e}"}
        print(f"llm_result: {len(llm_result)}")
        # Update database
        updates = {
            "content": content,
            "summary": llm_result["summary"],
            "publish_date": llm_result["publish_date"]
        }
        update_success = self.news_db.update_fields(
            url, **updates
        )
        
        if not update_success:
            return {"error": "Database update failed"}
        
        print("summary - done")
        return llm_result
    
    def batch_process_news_article(self, urls, job_id):
        url_record = self.news_db.fetch_records(urls)
        urls_to_sumarize = []
        for url in url_record:
            if url_record[url] is None:
                print(f"{url} - None")
                continue
            if url_record[url]["content"] == "pending":
                urls_to_sumarize.append(url)
                
        for url in urls_to_sumarize:
            print(f"processing url {url}")
            self.process_news_article(url)
            time.sleep(1)

        status = "sumaries ready"
        self.job_status.push_status(job_id, status)
        return True, urls
        
        
############

class NewsInsights:
    def __init__(self, 
                 news_db_path: str, 
                 fragment_db_path: str, 
                 system_prompt_path: str,
                 env_path: str
                ):
        """
        Initialize News Insights processor.
        """
        self.env_path = env_path
        self.news_db_path = news_db_path
        self.fragment_db_path = fragment_db_path
        self.system_prompt_path = system_prompt_path
        
        # Initialize databases
        self.news_db = dbs.NewsManager(news_db_path)
        self.job_db = rq.JobRegisterMg()
        self.fragment_db = dbs.NewsCropDatabase(fragment_db_path)
        
        # Load LLM configuration
        self.sys_prompt = self._load_system_prompt()
        self.api_key = self._load_api_key()
        self.headers = self._set_headers()
    
    def _load_system_prompt(self) -> str:
        """Load system prompt from file."""
        try:
            with open(self.system_prompt_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {self.system_prompt_path}")
    
    def _load_api_key(self) -> str:
        """Load API key from environment variables."""
        load_dotenv(self.env_path)
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("OPENAI_API_KEY not found in environment variables")
        return api_key
    
    def _set_headers(self) -> Dict[str, str]:
        """Set API headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
    
    def check_exist_relations(self, urls: List[str], ticker: str) -> List[str]:
        """
        Find URLs that don't have existing fragments for this ticker.
        
        Args:
            urls: List of URLs to check
            ticker: Ticker symbol
            
        Returns:
            List of URLs that need processing
        """
        new_urls = []
        for url in urls:
            print("-----", url, ticker)
            if not self.fragment_db.check_fragments(url, ticker):
                new_urls.append(url)
        
        print(f"Found {len(new_urls)} new URLs to process out of {len(urls)}")
        return new_urls
    
    def crop_insights(self, org: Optional[str], ticker: str, urls: List[str], job_id: str) -> bool:
        """
        Extract insights from news content for a specific company.
        """
        print(f"Starting insight extraction for {ticker} ({org}) with {len(urls)} URLs")
        
        processed_count = 0
        for url in urls:
            try:
                # Get news record
                news_record = self.news_db.get_record_by_url(url)
                if not news_record:
                    print(f"Skipping {url} - no news record found")
                    continue
                
                # Get content and publication date
                content = news_record.get('content', '')
                publish_date = news_record.get('publish_date', '')
                title = news_record.get('title', '')
                
                if not content or content == 'pending':
                    print(f"Skipping {url} - no content available")
                    continue
                
                # Call LLM for insight extraction
                llm_result = self._call_llm_insight(org, ticker, content, publish_date, title)
                # print(f" >> 2 result -- {llm_result}")
                
                if llm_result and llm_result.get('related_reason_simple') != 'no relation':
                    # Save fragment
                    fragment_data = {
                        "org": org or "",
                        "ticker": ticker,
                        "url": url,
                        "time_created": dt.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                        "related_reason_simple": llm_result.get('related_reason_simple', ''),
                        "related_reason_short": llm_result.get('related_reason_short', ''),
                        "polarity": llm_result.get('polarity', 'neutral'),
                        "title": title,
                        "actual_trend": llm_result.get('actual_trend', 'unknown'),
                        "quote_frag": llm_result.get('quote_frag', '')
                    }
                    self.save_fragment(fragment_data)
                    processed_count += 1
                
            except Exception as e:
                print(f"Error processing {url}: {e}")
                continue
        
        # Update job status
        self.job_db.push_status(job_id, f"news crops ready")
        print(f"Completed insight extraction for {ticker}. Processed: {processed_count}/{len(urls)}")
        return True
    
    def _call_llm_insight(self, org: Optional[str], ticker: str, content: str, publish_date: str, title: str):
        """
        Call LLM API for insight extraction.
        """
        user_msg = f"""
        Company: {org or 'Not specified'}
        Ticker: {ticker}
        Article Title: {title}
        Publication Date: {publish_date or 'Not specified'}
        
        News Content:
        {content[:8000]}  # Truncate very long content
        """
        
        messages = [
            {"role": "system", "content": self.sys_prompt},
            {"role": "user", "content": user_msg}
        ]
        
        payload = {
            "model": "gpt-5",
            "messages": messages,
            "response_format": { "type": "json_object" }
        }
        
        api_url = "https://api.openai.com/v1/chat/completions"
        
        try:
            response = requests.post(api_url, headers=self.headers, json=payload, timeout=60)
            
            if response.status_code != 200:
                raise RuntimeError(f"API call failed: {response.status_code} {response.text}")
            
            result = response.json()
            llm_output = result['choices'][0]['message']['content']
            # print(f" >> 1- result -- {result}")
            # Parse JSON response
            return json.loads(llm_output)
            
        except Exception as e:
            print(f"LLM API error: {e}")
            return None
    
    def save_fragment(self, fragment_data: Dict) -> int:
        """
        Save extracted fragment to database.
        """
        return self.fragment_db.insert_record(fragment_data)
    
    def process_job(self, job_id: str, org: Optional[str], ticker: str, urls: List[str]) -> bool:
        """
        Complete processing pipeline for a job.
        """
        try:
            print(job_id, "starting news insight extraction")
            
            # Check for existing fragments
            new_urls = self.check_exist_relations(urls, ticker)
            
            if not new_urls:
                self.job_db.push_status(job_id, "news crops ready")
                return True
            
            # Process insights
            success = self.crop_insights(org, ticker, new_urls, job_id)
            self.job_db.push_status(job_id, "news crops ready")
            return success
            
        except Exception as e:
            error_msg = f"Job failed: {e}"
            self.job_db.push_status(job_id, error_msg)
            raise RuntimeError(error_msg)