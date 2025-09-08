I have a stock insights system:

code structure:
- webUtils: download news for the ticker symbol
  - newsUtils.py 
    > class TickerCrawler
      this class firstly download the chart page from yahoo finance, then collect the news links then download the related articles    
      web crawl approach: playwrite to load local browser, mimic human browsing behavior
      comments 1: failed tries - rotate proxy, rotate agent, random fingerprinting - failed to get int most of the news vendor 
      comments 2: current solution is robust but not ideal
- LLMUtils: LLM tools to get the content insights
  - llmTools.py
    > class FinancialNewsSummarizor
      this class takes in the article and give summary - not much considered for now
    > class NewsInsights
      this class takes in a ticker - infer the company name - then ask LLM to pick the news fragments that are related to this company and gives the below insights:
      >> for what reason it is related (short and detailed) - considered as a relation item / event signal
      >> polarity - impact of the news mentions to the stock trend of the company
      >> actual stock trend  of the company at the news published day and a few days after - for historical stats of the relation item
      >> the UI can renders the stats of such relation item across all the tickers historically to give the profiling of the item - so the user can easily neglect or alerted to this signal 
      
- redis_q:
  - redisUtils.py: queue management - for demo only, and job logging
    > class RQJobQ
      shared by all the services
      gives three job queues:
      1. web crawl job queue 
         producer: UI backend push the job with [ticker, unique Job ID]
         consumer: web crawler
         on completion, register the job status
      2. LLM summarization process job:
         producer: web crawler, push the job with [ticker, org (from crawler), news urls, unique Job ID]
         consumer: LLM summarisor 
         on completion, register the job status
      3. LLM news cropping job que:
         producer: LLM summarisor push the job with [ticker, org (from crawler), news urls, unique Job ID]
         consumer: LLM news cropping and insight extractor
         on completion, register the job status - set the flag for process completion that to be captured by UI
    > class JobRegisterMg:
      job logging and status check manager, shared by all the services
      
- dbutils: I'm using TinyDB for demo, for serious development, cosmos, cassandra etc. are be preferred
  - db_classes.py
    storage for the data of difference processing levels and also the fetching, updating utils
    > class ChartDB:
      saves the chart page of the ticker, on which it has the news links. the items can be expired. but if the item is within a certain time range to now, we can skip the page downlaoding
      [ticker, org, [news urls], time dowloaded] - ticker centric, record can be expired
    > class NewsManager:
      stores news details [url, content, summary, create_time, etc.] - url/article centric
    > class NewsCropDatabase
      saves the news crops/fragments that specifically related to the ticker/company
      [url, title, create_time, reason_title, reason_descritpion, polarity, actual_trend] - url+ticker centric

App/Services:
- service 1: news dowloader
  service_1_news_downloader.ipynb
- service_2: news content scraping and summarisation
  service_2_news_summarisor.ipynb
- service_3: news cropping and insight extraction
  service_3_news_cropping.ipynb
- main App (UI backend): streamlit demo app
  news_insights_app.py
  
data:
- raw htmls
- DB - chart page
- DB - news
- DB - news crop / insights
- DB - statistics - not implemented - this will include the feedbacks and historical facts
- prompts

prompts:
- under data - I consider prompts as data for easy updating and maintenance by a side pipeline
       
secrets: for production suggest to use hashicorp, or other safe boxes / scope management
- use dotenv


Hilights/features
- avoid repeated search
- disaster resistent
- easy scaling up
- modulelized components
- resistent to single/multiple service failure
- avoid repeated search from different users for news or insights
- dynamically takes in statistics from feedback and historical facts/stats
- easy to extend/config
- user session insulation

