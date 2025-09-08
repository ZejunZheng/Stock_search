# Stock Insights System Architecture

## Code Structure

### Web Utilities: News Downloading
- **Location**: `webUtils/`
- **Main File**: `newsUtils.py`
- **Key Component**: `TickerCrawler` class
  - Downloads chart pages from Yahoo Finance
  - Collects and downloads related news articles
  - Uses Playwright for browser automation with human-like behavior

#### Implementation Notes:
- **Failed Approaches**: Proxy rotation, agent rotation, random fingerprinting (blocked by news vendors)
- **Current Solution**: Robust but not ideal web crawling approach

### LLM Utilities: Content Analysis
- **Location**: `LLMUtils/`
- **Main File**: `llmTools.py`
- **Key Components**:

#### 1. `FinancialNewsSummarizor` class
- Processes articles and generates summaries
- Currently in preliminary development stage

#### 2. `NewsInsights` class
- Takes ticker symbols, infers company names
- Uses LLM to extract relevant news fragments with insights:
  - **Relation Reason**: Short and detailed explanations of relevance
  - **Polarity**: Impact assessment on stock trends
  - **Actual Trend**: Historical stock performance around publication date
  - **UI Integration**: Historical statistics profiling for signal prioritization

### Redis Queue Management
- **Location**: `redis_q/`
- **Main File**: `redisUtils.py`
- **Purpose**: Demo and job logging system

#### Queue Architecture:
1. **Web Crawl Job Queue**
   - **Producer**: UI backend (ticker + unique Job ID)
   - **Consumer**: Web crawler service
   - **Completion**: Job status registration

2. **LLM Summarization Queue**
   - **Producer**: Web crawler (ticker, organization, news URLs, Job ID)
   - **Consumer**: LLM summarization service
   - **Completion**: Job status registration

3. **LLM News Cropping Queue**
   - **Producer**: LLM summarizer (ticker, organization, news URLs, Job ID)
   - **Consumer**: LLM insight extraction service
   - **Completion**: Process completion flag for UI capture

#### Supporting Class:
- `JobRegisterMg`: Job logging and status management (shared across services)

### Database Utilities
- **Location**: `dbutils/`
- **Main File**: `db_classes.py`
- **Current Implementation**: TinyDB (for demonstration)
- **Production Recommendation**: CosmosDB, Cassandra, or other scalable solutions

#### Database Classes:

#### 1. `ChartDB`
- Stores ticker chart pages with news links
- **Data Structure**: `[ticker, org, [news_urls], time_downloaded]`
- **Expiration**: Time-based record expiration with skip logic for recent downloads
- **Scope**: Ticker-centric storage

#### 2. `NewsManager`
- Manages news article details
- **Data Structure**: `[url, content, summary, create_time, etc.]`
- **Scope**: URL/article-centric storage

#### 3. `NewsCropDatabase`
- Stores news fragments relevant to specific tickers/companies
- **Data Structure**: `[url, title, create_time, reason_title, reason_description, polarity, actual_trend]`
- **Scope**: URL + ticker-centric relationship storage

## Application Services

### Service 1: News Downloader
- **File**: `service_1_news_downloader.ipynb`
- **Function**: Primary news content acquisition

### Service 2: News Content Processing
- **File**: `service_2_news_summarisor.ipynb`
- **Function**: Content scraping and summarization

### Service 3: Insight Extraction
- **File**: `service_3_news_cropping.ipynb`
- **Function**: News cropping and insight generation

### Main Application: User Interface
- **File**: `news_insights_app.py`
- **Framework**: Streamlit demo application
- **Role**: Frontend backend and user interaction

## Data Management

### Data Categories:
- **Raw HTMLs**: Source content storage
- **Chart Page Database**: Processed chart data
- **News Database**: Article content storage
- **News Insights Database**: Processed fragments and analysis
- **Statistics Database**: *Not yet implemented* - Will include user feedback and historical facts

### Prompt Management:
- **Location**: Under data directory
- **Strategy**: Treat prompts as data for easy maintenance and updates
- **Benefits**: Enables side pipeline for prompt management and versioning

## Security Implementation

### Secrets Management:
- **Current**: Dotenv for development
- **Production Recommendation**: Hashicorp Vault or secure scope management systems
- **Priority**: Secure credential handling and access control

## System Highlights & Features

### ✅ Efficiency & Performance
- **Duplicate Prevention**: Avoids repeated searches and processing
- **Disaster Resistant**: Robust failure recovery mechanisms
- **Scalability**: Designed for easy horizontal scaling

### ✅ Architecture Advantages
- **Modular Design**: Independent, replaceable components
- **Fault Tolerance**: Resistant to single/multiple service failures
- **User Isolation**: Session-based insulation for multi-user support

### ✅ Dynamic Capabilities
- **Adaptive Statistics**: Incorporates feedback and historical data
- **Extensible Design**: Easy to extend and configure
- **Real-time Updates**: Dynamic response to new information

### ✅ User Experience
- **Cross-user Optimization**: Prevents duplicate processing for different users
- **Historical Context**: Leverages past data for improved insights
- **Configurable**: Flexible system configuration options

---

**Technology Stack**: Python, Playwright, LLM Integration, Redis, TinyDB, Streamlit  
**Deployment Ready**: Modular architecture suitable for production scaling  
**Future Proof**: Designed for easy technology migration (database, LLM providers, etc.)
