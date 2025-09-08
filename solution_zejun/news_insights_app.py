import streamlit as st
import time
from datetime import datetime as dt
from typing import Dict, List, Optional
import redis
import json
import uuid
import sys
from tinydb import TinyDB, Query
from datetime import datetime as dt, timedelta
import os
from typing import List, Tuple, Optional, Dict, Any
import importlib
import uuid

root_path = "/Users/zejunzheng/Documents/GenAI/stock_searcher"  # Absolute path
sys.path.append(root_path)

import redis_q.redisUtils as rq # import RQJobQ
import dbutils.db_classes as dbs
import webUtils.newsUtils as news_cls
import config.conf as configure
import LLMUtils.llmTools as llm_tools

def set_recource():
    if 'job_checker' not in st.session_state:
        st.session_state.job_checker = rq.JobRegisterMg()
    if "frag_db" not in st.session_state:
        st.session_state.frag_db = dbs.NewsCropDatabase(configure.paths['frag_db'])
    if 'job_queue' not in st.session_state:
        st.session_state.job_queue = rq.RQJobQ()
    if 'user_id' not in st.session_state:
        st.session_state.user_id = ""
    if 'session_id' not in st.session_state:
        st.session_state.session_id = ""
    if 'attached' not in st.session_state:
        st.session_state.attached = False
    if 'current_job_id' not in st.session_state:
        st.session_state.current_job_id = None
    if 'job_status' not in st.session_state:
        st.session_state.job_status = "idle"
    if 'fragments' not in st.session_state:
        st.session_state.fragments = []
    if 'selected_fragment' not in st.session_state:
        st.session_state.selected_fragment = None
    if 'monitoring' not in st.session_state:
        st.session_state.monitoring = False
        
        
def user_session_attachment():
    
    st.header("User Session")
    col1, col2, col3 = st.columns([2, 2, 1])

    with col1:
        user_id = st.text_input("User ID", value=st.session_state.user_id, 
                               placeholder="Enter your user ID")
    with col2:
        session_id = st.text_input("Session ID", value=st.session_state.session_id,
                                  placeholder="Enter session ID")
    with col3:
        attach_btn = st.button("Attach", type="primary")

    if attach_btn:
        if user_id and session_id:
            st.session_state.user_id = user_id
            st.session_state.session_id = session_id
            st.session_state.attached = True
            st.success(f"Attached: User {user_id}, Session {session_id}")
        else:
            st.error("Please enter both User ID and Session ID")

    if not st.session_state.attached:
        st.info("Please attach a user session to continue")
        return False

    return True

    
def render_insight_panel(left_panel):
    with left_panel:
        st.subheader("Insight Panel")
        
        # Query input
        col_query, col_btn = st.columns([3, 1])
        with col_query:
            ticker = st.text_input("Ticker Symbol", placeholder="e.g., 0005.HK, AAPL", 
                                  key="ticker_input")
        with col_btn:
            query_btn = st.button("Query News", type="primary")
        
        # st.write(f"** here -- redis_client {ticker} **")
        
        if query_btn:
            ticker = ticker.upper()
            if len(ticker) == 0:
                st.write(f"** empty ticker - {ticker} **")
                return 
            # Generate job ID
            job_id = f"{st.session_state.user_id}@{st.session_state.session_id}@{ticker}@{uuid.uuid4().hex[:8]}"
            st.session_state.current_job_id = job_id
            st.session_state.job_status = "submitted"
            st.session_state.monitoring = True
            # st.write("** here -- redis_client **")
            
            # Push job to Redis queue
            
            try:
                st.session_state.job_queue.push_crawler_job(job_id, ticker)
                num_jobs_in_q = st.session_state.job_queue.RQ.llen(st.session_state.job_queue.crawl_queue_name)
                st.success(f"Job submitted: {job_id} - currently there are {num_jobs_in_q} jobs in the que")
            except Exception as e:
                st.error(f"Failed to submit job: {e}")
                st.session_state.job_status = "failed"
                st.session_state.monitoring = False
        
        # Job monitoring section
        if st.session_state.monitoring and st.session_state.current_job_id:
            st.subheader("Job Status")
            
            # Create progress area
            status_placeholder = st.empty()
            progress_placeholder = st.empty()
            max_retries = 20
            retry_interval = 5  # seconds
            
            for attempt in range(max_retries):
                # Check job status
                status = st.session_state.job_checker.get_job_status(st.session_state.current_job_id)
                
                st.session_state.job_status = status
                
                # Update status display
                status_placeholder.info(f"Status: {status} (Attempt {attempt + 1}/{max_retries})")
                progress_placeholder.progress((attempt + 1) / max_retries)
                
                # Check if job is completed
                if "news crops ready" in status.lower():
                    status_placeholder.success(f"✅ Job completed: {status}")
                    progress_placeholder.empty()
                    
                    # Fetch fragments
                    fragments_result = st.session_state.frag_db.fetch_records(ticker)
                    
                    if len(fragments_result) > 0:
                        st.session_state.fragments = fragments_result
                        st.session_state.monitoring = False
                    break
                
                # Check if job failed
                if "fail" in status.lower() or "error" in status.lower():
                    status_placeholder.error(f"❌ Job failed: {status}")
                    progress_placeholder.empty()
                    st.session_state.monitoring = False
                    break
                
                # Wait for next check
                time.sleep(retry_interval)
            
            else:  # Max retries reached
                status_placeholder.warning("⏰ Server is busy. Please try again later.")
                progress_placeholder.empty()
                st.session_state.monitoring = False
        
        # Display insights if available
        if st.session_state.fragments:
            st.subheader(f"Insights ({len(st.session_state.fragments)} found)")
            
            for i, fragment in enumerate(st.session_state.fragments):
                # Create card for each fragment
                with st.expander(f"Insight {i+1}: {fragment.get('related_reason_simple', 'N/A')}", expanded=False):
                    col_info, col_btn = st.columns([3, 1])
                    
                    with col_info:
                        st.write(f"**Ticker:** {fragment.get('ticker', 'N/A')}")
                        st.write(f"**Event:** {fragment.get('related_reason_simple', 'N/A')}")
                        st.write(f"**Insight:** {fragment.get('related_reason_short', 'N/A')}")
                        st.write(f"**Polarity:** {fragment.get('polarity', 'N/A')}")
                        st.write(f"**Source:** {fragment.get('url', 'N/A')}")
                    
                    with col_btn:
                        if st.button("View Details", key=f"detail_btn_{i}"):
                            st.session_state.selected_fragment = fragment
            
            # Additional query section
            st.subheader("Additional Queries")
            additional_query = st.text_area("Enter your additional query:", 
                                          placeholder="Ask about specific insights or patterns...",
                                          height=100)
            
            if st.button("Submit Query"):
                # Placeholder for additional query processing
                st.session_state.selected_fragment = {"query_response": "To be added: " + additional_query}
                
                
def render_detail_panel(right_panel):
    with right_panel:
        st.subheader("Detail Panel")
        
        if st.session_state.selected_fragment:
            fragment = st.session_state.selected_fragment
            
            if "query_response" in fragment:
                # Show query response
                st.write("**Query Response:**")
                st.info(fragment["query_response"])
            else:
                # Show fragment details
                st.write("**Detailed Fragment Information:**")
                
#                 detail_fields = [
#                     ("URL", "url"),
#                     ("Title", "title"),
#                     ("Organization", "org"),
#                     ("Ticker", "ticker"),
#                     ("Related Reason (Simple)", "related_reason_simple"),
#                     ("Related Reason (Detailed)", "related_reason_short"),
#                     ("Polarity", "polarity"),
#                     ("Actual Trend", "actual_trend"),
#                     ("Quote Fragment", "quote_frag"),
#                     ("Time Created", "time_created")
#                 ]
                
#                 for field_name, field_key in detail_fields:
#                     if field_key in fragment and fragment[field_key]:
#                         st.write(f"**{field_name}:**")
#                         st.text_area("", fragment[field_key], height=100 if field_key == "quote_frag" else 60, 
#                                     key=f"detail_{field_key}", label_visibility="collapsed")
                
                # Raw JSON view
                with st.expander("Raw JSON Data"):
                    st.json(fragment)
        else:
            st.info("Select an insight or submit a query to see details here.")
    
    # Footer with session info
    st.sidebar.header("Session Information")
    st.sidebar.write(f"**User:** {st.session_state.user_id}")
    st.sidebar.write(f"**Session:** {st.session_state.session_id}")
    st.sidebar.write(f"**Current Job:** {st.session_state.current_job_id or 'None'}")
    st.sidebar.write(f"**Job Status:** {st.session_state.job_status}")
    
    if st.sidebar.button("Reset Session"):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
        
if __name__ == "__main__":
    set_recource()
    # Part 1: User Attachment
    user_session_attachment()

    # Part 2: Query Bench
    st.header("News Insights Query")

    # Create two columns for left and right panels
    left_panel, right_panel = st.columns([2, 1]) 

    # render left panel
    render_insight_panel(left_panel)

    # render the right panel
    render_detail_panel(right_panel)
