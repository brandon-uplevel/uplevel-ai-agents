#!/usr/bin/env python3
"""
Mock Sales & Marketing Intelligence Agent for Frontend Testing
This is a simplified version for testing the multi-agent frontend integration.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import uuid
from datetime import datetime

# FastAPI app setup
app = FastAPI(
    title="Sales & Marketing Intelligence Agent (Mock)",
    description="Mock agent for frontend testing",
    version="1.0.0"
)

# CORS middleware for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data models
class SalesQuery(BaseModel):
    query: str
    session_id: Optional[str] = None

class SalesResponse(BaseModel):
    response: str
    session_id: str
    agent_type: str = "sales_marketing"
    timestamp: str

# In-memory storage for demo
sessions = {}

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "agent": "Sales & Marketing Intelligence Agent (Mock)",
        "version": "1.0.0",
        "status": "active",
        "capabilities": [
            "Lead Management",
            "Sales Pipeline Analysis", 
            "Campaign Performance",
            "Customer Segmentation",
            "Revenue Forecasting"
        ]
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/query", response_model=SalesResponse)
async def process_query(query: SalesQuery):
    """Process sales and marketing queries"""
    
    # Generate session ID if not provided
    session_id = query.session_id or str(uuid.uuid4())
    
    # Initialize session if new
    if session_id not in sessions:
        sessions[session_id] = {
            "messages": [],
            "created_at": datetime.now().isoformat()
        }
    
    # Add query to session
    sessions[session_id]["messages"].append({
        "type": "query",
        "content": query.query,
        "timestamp": datetime.now().isoformat()
    })
    
    # Generate mock response based on query content
    response_text = generate_mock_response(query.query.lower())
    
    # Add response to session
    sessions[session_id]["messages"].append({
        "type": "response", 
        "content": response_text,
        "timestamp": datetime.now().isoformat()
    })
    
    return SalesResponse(
        response=response_text,
        session_id=session_id,
        timestamp=datetime.now().isoformat()
    )

def generate_mock_response(query: str) -> str:
    """Generate contextual mock responses"""
    
    if any(word in query for word in ["lead", "prospect", "contact"]):
        return """I can help you with lead management! Here are some key insights:

📊 **Current Lead Status:**
- Active Leads: 45 prospects in pipeline
- Hot Leads: 12 ready for immediate outreach
- Converted This Month: 8 leads (18% conversion rate)

🎯 **Lead Sources:**
- LinkedIn: 60% of qualified leads
- Email campaigns: 25%
- Referrals: 15%

💡 **Recommendations:**
- Focus on LinkedIn prospects with 500+ connections
- Follow up with hot leads within 24 hours
- A/B test email subject lines to improve open rates

Would you like me to analyze specific lead segments or create outreach templates?"""

    elif any(word in query for word in ["campaign", "marketing", "email"]):
        return """📈 **Campaign Performance Dashboard:**

**Recent Email Campaigns:**
- "Q4 Product Launch": 24% open rate, 4.2% CTR
- "Holiday Special": 31% open rate, 6.1% CTR  
- "Customer Success Stories": 19% open rate, 2.8% CTR

**Top Performing Segments:**
1. Enterprise prospects (45% engagement)
2. Returning customers (38% engagement)
3. Free trial users (29% engagement)

**Optimization Opportunities:**
- Personalize subject lines (+15% open rate)
- Add video thumbnails (+23% CTR)
- Test send times (Tuesday 10am performs best)

Want me to create a new campaign strategy or analyze specific metrics?"""

    elif any(word in query for word in ["sales", "pipeline", "revenue"]):
        return """💰 **Sales Pipeline Analysis:**

**Current Pipeline Status:**
- Total Pipeline Value: $485K
- Deals in Progress: 23
- Average Deal Size: $21K
- Expected Close Rate: 65%

**Stage Breakdown:**
- Discovery: 8 deals ($156K)
- Proposal: 9 deals ($198K) 
- Negotiation: 4 deals ($89K)
- Closing: 2 deals ($42K)

**Revenue Forecast:**
- This Month: $89K (92% confidence)
- Next Month: $127K (78% confidence)
- Q1 Target: $340K (on track)

🚀 **Action Items:**
- Follow up on 4 stalled discovery calls
- Send proposals to 3 qualified prospects
- Schedule closing calls for 2 hot deals

Need help with specific deals or want to dive deeper into any stage?"""

    elif any(word in query for word in ["customer", "segment", "analysis"]):
        return """🎯 **Customer Segmentation Insights:**

**Primary Segments:**
1. **Enterprise** (35% of revenue)
   - Avg. Deal Size: $45K
   - Decision Time: 120 days
   - Key Pain Point: Scalability

2. **Mid-Market** (45% of revenue)  
   - Avg. Deal Size: $18K
   - Decision Time: 60 days
   - Key Pain Point: Efficiency

3. **SMB** (20% of revenue)
   - Avg. Deal Size: $5K  
   - Decision Time: 30 days
   - Key Pain Point: Cost

**Behavioral Insights:**
- Enterprise: Prefers demos, case studies
- Mid-Market: Values ROI calculations, trials
- SMB: Needs quick implementation, support

**Recommendations:**
- Create segment-specific landing pages
- Tailor pricing strategies per segment
- Develop targeted content for each persona

Want me to analyze a specific segment or create targeted campaigns?"""

    else:
        return f"""Hello! I'm your Sales & Marketing Intelligence Agent. I can help you with:

🎯 **Lead Management**
- Track prospect engagement and scoring
- Optimize outreach sequences and timing
- Analyze lead sources and conversion rates

📊 **Sales Pipeline Analysis** 
- Monitor deal progression and bottlenecks
- Forecast revenue with confidence intervals
- Identify at-risk opportunities

📈 **Campaign Performance**
- Email marketing analytics and optimization
- Customer segmentation and targeting
- ROI analysis across marketing channels

💰 **Revenue Operations**
- Sales forecasting and quota tracking  
- Customer lifetime value analysis
- Pricing strategy optimization

Ask me about your leads, campaigns, pipeline, or customers and I'll provide actionable insights!

*Your query: "{query[:100]}..."*"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
