"""
Web tools for search, page retrieval, weather, world news, and finance news.
"""

import httpx
import xml.etree.ElementTree as ET
import asyncio
import re
import webbrowser
from friday.search import get_weather_report, google_web_search

# General news sources.
SEED_FEEDS = [
    'https://feeds.bbci.co.uk/news/world/rss.xml',
    'https://www.cnbc.com/id/100727362/device/rss/rss.html',
    'https://rss.nytimes.com/services/xml/rss/nyt/World.xml',
    'https://www.aljazeera.com/xml/rss/all.xml'
]

# Finance news sources.
FINANCE_SEED_FEEDS = [
    'https://www.cnbc.com/id/10000664/device/rss/rss.html',        # CNBC Finance
    'https://feeds.bloomberg.com/markets/news.rss',                # Bloomberg Markets
    'https://www.reutersagency.com/feed/?taxonomy=best-sectors&post_type=best',  # Reuters
    'https://feeds.marketwatch.com/marketwatch/topstories/',       # MarketWatch
    'https://rss.nytimes.com/services/xml/rss/nyt/Business.xml',   # NYT Business
]

async def fetch_and_parse_feed(client, url):
    """Fetch and parse one RSS feed."""
    try:
        response = await client.get(url, headers={'User-Agent': 'Friday-AI/1.0'}, timeout=5.0)
        if response.status_code != 200:
            return []

        root = ET.fromstring(response.content)
        # Derive a compact source label from the feed URL.
        parts = url.split('.')
        source_name = parts[1].upper() if len(parts) > 1 else "NEWS"
        
        feed_items = []
        # Keep at most five items from each source.
        items = root.findall(".//item")[:5]
        for item in items:
            title = item.findtext("title")
            description = item.findtext("description")
            link = item.findtext("link")
            
            if description:
                # Strip HTML from feed descriptions.
                description = re.sub('<[^<]+?>', '', description).strip()

            feed_items.append({
                "source": source_name,
                "title": title,
                "summary": description[:200] + "..." if description else "",
                "link": link
            })
        return feed_items
    except Exception:
        # One failed feed must not prevent the remaining feeds from loading.
        return []

def register(mcp):

    @mcp.tool()
    async def get_world_news() -> str:
        """
        Fetch the latest world headlines from major sources concurrently.
        """
        
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in SEED_FEEDS]
            results_of_lists = await asyncio.gather(*tasks)
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The world news feeds are not responding, boss. I could not retrieve current headlines."

        report = ["### LIVE WORLD NEWS BRIEF\n"]
        for entry in all_articles[:12]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    # Finance news tool.
    @mcp.tool()
    async def get_world_finance_news() -> str:
        """
        Fetch current finance and market headlines from major sources.
        """
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            tasks = [fetch_and_parse_feed(client, url) for url in FINANCE_SEED_FEEDS]
            results_of_lists = await asyncio.gather(*tasks)
            all_articles = [item for sublist in results_of_lists for item in sublist]

        if not all_articles:
            return "The finance feeds are not responding, boss. I could not retrieve a market update."

        report = ["### LIVE FINANCE BRIEF\n"]
        for entry in all_articles[:12]:
            report.append(f"**[{entry['source']}]** {entry['title']}")
            report.append(f"{entry['summary']}")
            report.append(f"Link: {entry['link']}\n")

        return "\n".join(report)

    @mcp.tool()
    async def search_web(query: str) -> str:
        """Search the web and return a grounded summary."""
        return await asyncio.to_thread(google_web_search, query=query)

    @mcp.tool()
    async def get_weather(city: str, country: str = "Vietnam") -> str:
        """
        Fetch current weather and a short forecast for a city.
        """
        return await get_weather_report(city=city, country=country)

    @mcp.tool()
    async def fetch_url(url: str) -> str:
        """Fetch the text content of a URL."""
        async with httpx.AsyncClient(follow_redirects=True, timeout=10) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.text[:4000]
    
    @mcp.tool()
    async def open_world_monitor() -> str:
        """
        Open World Monitor in the system browser.
        """
        url = "https://worldmonitor.app/"
        try:
            webbrowser.open(url)
            return "Opened World Monitor in your browser, boss."
        except Exception as e:
            return f"I could not open World Monitor: {str(e)}"

    # Finance Monitor tool.
    @mcp.tool()
    async def open_finance_world_monitor() -> str:
        """
        Open Finance Monitor in the system browser.
        """
        url = "https://finance.worldmonitor.app/"
        try:
            webbrowser.open(url)
            return "Opened Finance Monitor in your browser, boss."
        except Exception as e:
            return f"I could not open Finance Monitor: {str(e)}"
