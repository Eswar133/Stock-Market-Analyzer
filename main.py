# File: app/main.py
import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from textblob import TextBlob
import requests
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def load_stock_data(ticker: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Load stock data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(start=start_date, end=end_date)
        if data.empty:
            st.error(f"No data found for {ticker}. Please check the ticker symbol and date range.")
            return pd.DataFrame()
        return data
    except Exception as e:
        logging.error(f"Error loading stock data: {e}")
        st.error(f"An error occurred while loading data for {ticker}. Please try again.")
        return pd.DataFrame()

def calculate_moving_averages(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate moving averages for the stock data."""
    data['SMA_20'] = data['Close'].rolling(window=20).mean()
    data['SMA_50'] = data['Close'].rolling(window=50).mean()
    return data

def calculate_rsi(data: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """Calculate Relative Strength Index (RSI)."""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))
    return data

def create_chart(data: pd.DataFrame) -> go.Figure:
    """Create an interactive chart using Plotly."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['Close'], name="Close Price"))
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_20'], name="20-day SMA"))
    fig.add_trace(go.Scatter(x=data.index, y=data['SMA_50'], name="50-day SMA"))
    fig.update_layout(
        title="Stock Price and Moving Averages",
        xaxis_title="Date",
        yaxis_title="Price",
        legend_title="Indicators",
        hovermode="x unified"
    )
    return fig

def create_rsi_chart(data: pd.DataFrame) -> go.Figure:
    """Create an RSI chart using Plotly."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=data.index, y=data['RSI'], name="RSI"))
    fig.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="Overbought (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="Oversold (30)")
    fig.update_layout(
        title="Relative Strength Index (RSI)",
        xaxis_title="Date",
        yaxis_title="RSI",
        yaxis=dict(range=[0, 100])
    )
    return fig

# Load environment variables from .env file
load_dotenv()

# Get the API key 
api_key = os.environ.get("API_KEY")

def fetch_news(api_key, ticker):
    """Fetch news articles for a specific stock ticker."""
    url = f"https://newsapi.org/v2/everything?q={ticker}&apiKey={api_key}&language=en&sortBy=publishedAt&pageSize=5"
    response = requests.get(url)
    if response.status_code != 200:
        logging.error("Failed to fetch the news")
        return []
    news_data = response.json()
    articles = news_data.get("articles", [])
    
    # Perform sentiment analysis on each article's title
    news_sentiment = []
    for article in articles:
        title = article["title"]
        description = article.get("description", "No description available")
        sentiment = TextBlob(title).sentiment.polarity
        news_sentiment.append({"title": title, "description": description, "sentiment": sentiment})
    return news_sentiment

def main():
    st.set_page_config(page_title="Advanced Stock Market Analyzer", layout="wide")
    st.title("Advanced Stock Market Analyzer")
    
    # Sidebar for user input
    st.sidebar.header("Input Parameters")
    ticker = st.sidebar.text_input("Enter stock ticker:", value="AAPL").upper()
    start_date = st.sidebar.date_input("Start date", value=datetime.now() - timedelta(days=365))
    end_date = st.sidebar.date_input("End date", value=datetime.now())

    if st.sidebar.button("Analyze"):
        logging.info(f"Analyzing stock: {ticker} from {start_date} to {end_date}")
        
        # Load and process data
        data = load_stock_data(ticker, start_date, end_date)
        if not data.empty:
            data = calculate_moving_averages(data)
            data = calculate_rsi(data)
            
            # Display stock information
            st.header(f"{ticker} Stock Analysis")
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${data['Close'].iloc[-1]:.2f}")
            col2.metric("50-day SMA", f"${data['SMA_50'].iloc[-1]:.2f}")
            col3.metric("RSI", f"{data['RSI'].iloc[-1]:.2f}")
            
            # Create and display charts
            price_chart = create_chart(data)
            st.plotly_chart(price_chart, use_container_width=True)
            
            rsi_chart = create_rsi_chart(data)
            st.plotly_chart(rsi_chart, use_container_width=True)
            
            # Technical analysis
            st.subheader("Technical Analysis")
            last_close = data['Close'].iloc[-1]
            sma_20 = data['SMA_20'].iloc[-1]
            sma_50 = data['SMA_50'].iloc[-1]
            rsi = data['RSI'].iloc[-1]
            
            if last_close > sma_20 > sma_50:
                st.write("The stock is in an uptrend. The current price is above both the 20-day and 50-day SMAs.")
            elif last_close < sma_20 < sma_50:
                st.write("The stock is in a downtrend. The current price is below both the 20-day and 50-day SMAs.")
            else:
                st.write("The stock is showing mixed signals. Consider additional indicators for a clearer picture.")
            
            if rsi > 70:
                st.write("The RSI indicates that the stock may be overbought.")
            elif rsi < 30:
                st.write("The RSI indicates that the stock may be oversold.")
            else:
                st.write("The RSI is neutral, indicating neither overbought nor oversold conditions.")
                
            # Fetch and display news with sentiment analysis
            st.subheader(f"Recent News for {ticker}")
            news_data = fetch_news(api_key, ticker)
            
            if news_data:
                for news_item in news_data:
                    title = news_item["title"]
                    description = news_item["description"]
                    sentiment = news_item["sentiment"]
                    sentiment_text = "Positive" if sentiment > 0 else "Negative" if sentiment < 0 else "Neutral"
                    sentiment_color = "green" if sentiment > 0 else "red" if sentiment < 0 else "gray"
                    
                    st.markdown(f"**{title}**")
                    st.write(description)
                    st.markdown(f"<span style='color:{sentiment_color}'>Sentiment: {sentiment_text} ({sentiment:.2f})</span>", unsafe_allow_html=True)
                    st.write("---")
            else:
                st.write("No recent news found.")

if __name__ == "__main__":
    main()
