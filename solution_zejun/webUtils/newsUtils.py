import asyncio
import random
import urllib.parse
from typing import List, Dict, Optional
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import os
from datetime import datetime as dt

import dbutils.db_classes as dbs
import redis_q.redisUtils as rq

import time

class TickerCrawler:
    def __init__(self, raw_html_folder, charDB_path, newsDB_path):
        self.raw_html_folder = raw_html_folder
        self.base_url_chat = "https://sg.finance.yahoo.com/quote/"
        self.down_load_sleep_base = 5
        self.chart_db = dbs.ChartDB(charDB_path)
        self.news_db = dbs.NewsManager(newsDB_path)
        self.job_status = rq.JobRegisterMg()
    
    async def _download_url(self, url):
        async with async_playwright() as p:
            browser = await p.chromium.launch_persistent_context(
                user_data_dir="/Users/zejunzheng/chrome_secured", 
                headless=False,
                executable_path="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
            )

            page = await browser.new_page()
            await page.goto(url, timeout=150000)

            html = await page.content()
            print(len(html))  

            await browser.close()
            return html
    
    async def download_main_pages(self, tickers):
        sleep_time = self.down_load_sleep_base + random.uniform(2.0, 4.9)
        output_files = []
        for ticker in tickers:
            print(f"processing...{ticker}")
            url = f"{self.base_url_chat}{ticker}/"
            html = await self._download_url(url)

            output_path_tk = self.raw_html_folder + "/" + ticker
            os.makedirs(output_path_tk, exist_ok=True)
            output_file_name = ticker + "_TM_" + dt.utcnow().strftime("%Y-%m-%d_T_%H-%M-%S") + ".html"
            output_file_html = output_path_tk + "/" + output_file_name
            output_files.append(output_file_html)
            with open(output_file_html, "w") as fout:
                fout.write(html)
            time.sleep(sleep_time)
        print("- Done")
        return output_files
    
 
    def _extract_links_data_from_chart(self, html_content: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html_content, 'html.parser')
        org = soup.find('div', class_='name yf-1c9i0iv').get('title')

        # Find all <a> elements with the specific classes
        links = soup.find_all('a', class_='subtle-link fin-size-small titles noUnderline yf-1btaiiq')

        results = []
        for link in links:
            href = link.get('href')
            if "sg.finance.yahoo.com/news" not in href:
                continue
            title = link.get('title')

            if href and title:  # Only include if both are present
                results.append({
                    'href': href,
                    'title': title
                })

        return results, org
    
    async def _download_stk_news(self, ticker, urls):
        sleep_time = self.down_load_sleep_base + random.uniform(2.0, 4.9)
        output_files = []
        for url in urls:
            print(f"processing...{ticker}")

            html = await self._download_url(url)

            output_path_tk = self.raw_html_folder + "/" + ticker
            os.makedirs(output_path_tk, exist_ok=True)
            output_file_name = ticker + "_news_TM_" + dt.utcnow().strftime("%Y-%m-%d_T_%H-%M-%S") + ".html"
            output_file_html = output_path_tk + "/" + output_file_name
            output_files.append(output_file_html)
            with open(output_file_html, "w") as fout:
                fout.write(html)

            time.sleep(sleep_time)
        print("- Done")
        return output_files
    
    async def _dowload_news_and_record(self, file_path, ticker, max_n = 5):
        with open(file_path, 'r', encoding='utf-8') as file:
            html_content_news = file.read()

        news_data = dict()
        news_set, org = self._extract_links_data_from_chart(html_content_news)

        articles_with_html = []
        for idx, news in enumerate(news_set[0:max_n]):
            news_data[news['href']] = news['title']

        
        initial_urls = list(news_data.keys())
        url_rcds = self.news_db.fetch_records(initial_urls)
        
        to_download_ruls = [x for x, y in url_rcds.items() if (y is None)]
        
        htmls = await self._download_stk_news(ticker, to_download_ruls)
        new_htmls = zip(to_download_ruls, htmls)
        for new_url, html_file in new_htmls:
            self.news_db.push_record_initial(new_url, news_data[new_url], html_file)
            print(f" - inserted new html: {new_url}")
        
        return initial_urls, org
    
    async def find_or_download_news_urls(self, ticker, job_id):
        print("check the previous chart downloads ...")
        url_keys, time_created_str, expired, org = self.chart_db.check_latest(ticker)
        print(url_keys, time_created_str, expired, org)
        # download the char page then refind the urls, if the url in the mews DB, then skip, 
        # otherwise download and insert the record
        if expired: 
            print("previous downloads expired ...triggering new dowloads...")
            output_files = await self.download_main_pages([ticker])
            if len(output_files) == 0:
                raise ValueError(" -- Error: no out put file ---- .")
            print("chart page processing done.   dowloading news ...")
            output_file = output_files[0]
            urls_checked, org = await self._dowload_news_and_record(output_file, ticker, max_n = 5)
            print("news page processing done.   add records ...")
            self.chart_db.insert_record(ticker, urls_checked, org)
            url_keys = urls_checked
        print(f" news are ready for ticker: {ticker}")
        status = f"news ready {job_id}"
        self.job_status.push_status(job_id, status)
        return True, url_keys, org