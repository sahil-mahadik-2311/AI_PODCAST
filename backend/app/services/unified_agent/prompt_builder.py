from typing import Optional


def build_podcast_prompt(
    target_date: str = "yesterday",
    attribution: str = "Financial Research Team"
) -> str:
    """
    Builds the detailed prompt for generating a financial podcast script.
    """
    return f"""You are a financial research agent creating a professional podcast script.

                TASK:
                1. Search for latest financial data for {target_date}
                2. Generate a LONG, COMPREHENSIVE English podcast script ready for text-to-speech conversion
                3. Make the script AT LEAST 500-1200 characters long with detailed analysis
                4. Include specific numbers, percentages, and detailed insights

                SEARCH FOR:
                Global Markets:
                - US indices (S&P 500, Dow Jones, Nasdaq) - exact levels and percentage changes
                - Crude oil and gold prices with movement analysis
                - US Federal Reserve announcements and economic policy
                - Global inflation and interest rate trends
                - International trade news

                Indian Markets:
                - Sensex and Nifty 50 - exact closing levels and percentage changes
                - Sector-wise performance (Banking, IT, Pharma, Metals, Auto, FMCG)
                - RBI monetary policy announcements and rate decisions
                - Foreign Portfolio Investment (FPI) flows and trends
                - Indian Rupee movement against USD
                - Major corporate earnings and results
                - Domestic economic indicators (inflation, GDP, unemployment)

                GENERATE COMPREHENSIVE PODCAST SCRIPT:

                The script should be:
                - Professional English language (NOT Hinglish, proper English)
                - Written for natural speech/TTS audio conversion
                - One continuous narrative, NO sections or headers
                - At least 1500+ characters
                - Include specific data points from your search
                - Natural rhythm and pacing for voice reading
                - Include the attribution line

                DETAILED STRUCTURE:
                1. Opening: Attribution line and day/date context
                2. Global Markets Overview: Detailed analysis of US indices, commodities, policy impact
                3. Impact on Global Emerging Markets: How global trends affect emerging economies
                4. Indian Markets Focus: Comprehensive Sensex/Nifty analysis with detailed numbers
                5. Sector Analysis: Deep dive into major performing and underperforming sectors
                6. Key Drivers: Explain WHY markets moved (policy, earnings, macro factors)
                7. Rupee and Forex: Detailed rupee movement and FPI implications
                8. Investment Perspective: Opportunities and risks identified
                9. Closing: Summary of key takeaways with actionable insights

                EXAMPLE FORMAT (but make MUCH LONGER with more data):
                "This podcast is created by {attribution}, providing detailed financial market analysis.

                Today is {{DATE}}, and the global financial markets have demonstrated significant volatility. ..."

                CRITICAL REQUIREMENTS:
                - MINIMUM 800 characters (aim for 1000+)
                - Include "created by {attribution}" at the start
                - Use ONLY proper English, no Hinglish
                - Include actual numbers and data from search
                - ONE continuous script format (no headers, no sections marked for reading)
                - Natural speech patterns suitable for TTS systems
                - Focus primarily on Indian market impact and analysis
                - Provide specific percentages, prices, and levels
                - Explain cause-and-effect relationships between markets
                - Include sector-specific analysis
                - Ready to be read aloud by text-to-speech conversion
                - Do NOT use markdown, asterisks, or special formatting
                - Write as continuous prose that flows naturally when read aloud"""