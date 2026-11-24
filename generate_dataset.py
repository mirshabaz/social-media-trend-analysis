import csv
import random
from datetime import datetime, timedelta

random.seed(42)

# Templates and content by category / trend
topics_data = [
    {
        "category": "Artificial Intelligence",
        "hashtags": ["#AI", "#MachineLearning", "#TechTrends", "#Innovation", "#GenerativeAI", "#DataScience"],
        "posts": [
            ("Generative AI is completely reshaping how software engineering teams build products. The efficiency gains are undeniable!", "Positive"),
            ("Deep learning models are achieving state-of-the-art results in healthcare imaging. Truly life-saving tech! 🩺💡", "Positive"),
            ("Worried about the ethical implications and job displacement caused by rapid AI automation. Are we regulating fast enough?", "Negative"),
            ("Attending the annual global AI conference today. Lots of discussions on foundation models and multimodal systems.", "Neutral"),
            ("The new open-source LLM benchmark shows exciting open competition against proprietary models! #OpenSource", "Positive"),
            ("AI hallucinations in critical enterprise applications remain a persistent headache for developers.", "Negative"),
            ("Exploring transformer architectures for natural language understanding today. Solid mathematical foundations.", "Neutral"),
            ("Just implemented our first automated ML pipeline. Deployment time dropped from days to minutes!", "Positive"),
            ("Is the AI hype bubble going to burst soon, or is this truly the fourth industrial revolution?", "Neutral"),
            ("Autonomous agents failing on basic edge cases proves we still have a very long road ahead.", "Negative"),
            ("Incredible breakthrough in quantum computing applied to AI optimization algorithms announced this morning.", "Positive"),
            ("Data privacy concerns rise as corporate models continue training on unconsented web-scraped data.", "Negative")
        ]
    },
    {
        "category": "Remote Work & Career",
        "hashtags": ["#RemoteWork", "#CareerGrowth", "#FutureOfWork", "#Productivity", "#WorkLifeBalance", "#TechJobs"],
        "posts": [
            ("Working remotely has saved me 2 hours of commuting daily. My mental health and productivity have never been better. 🏡✨", "Positive"),
            ("Companies mandating 5 days return to office are losing their best senior engineering talent to competitors.", "Negative"),
            ("Setting healthy boundaries between work and personal life is essential when your living room is your office.", "Neutral"),
            ("Mentoring junior developers remotely is rewarding, but requires much more deliberate asynchronous communication.", "Positive"),
            ("Exhausted from back-to-back Zoom meetings that could easily have been a well-structured Slack message.", "Negative"),
            ("Shared tips on how to negotiate tech compensation during economic downturns on my latest blog post.", "Neutral"),
            ("Celebrated my promotion to Lead Data Scientist today! Grateful for a supportive remote team and mentors.", "Positive"),
            ("Isolation and lack of spontaneous team camaraderie can make prolonged remote work mentally draining.", "Negative"),
            ("Hybrid work models appear to strike the best balance for team collaboration and individual focus.", "Neutral"),
            ("Building an ergonomic home office setup was the single best investment I made this quarter.", "Positive")
        ]
    },
    {
        "category": "Cybersecurity & Privacy",
        "hashtags": ["#CyberSecurity", "#DataPrivacy", "#InfoSec", "#CloudSecurity", "#ZeroTrust"],
        "posts": [
            ("Another massive credential stuffing attack hits millions of users. Please enable multi-factor authentication everywhere! 🔐", "Negative"),
            ("Zero Trust architecture isn't just a buzzword; it's an operational necessity for modern distributed systems.", "Neutral"),
            ("Successfully prevented a major ransomware intrusion thanks to real-time endpoint anomaly detection. Huge win!", "Positive"),
            ("Phishing emails are becoming shockingly convincing with generative AI language drafting.", "Negative"),
            ("Reviewing new data privacy regulations passed by the EU. Compliance requirements are getting significantly stricter.", "Neutral"),
            ("Kudos to our SecOps team for achieving zero security downtime during peak Black Friday traffic!", "Positive"),
            ("Critical zero-day vulnerability discovered in popular open-source logging library. Patch immediately!", "Negative"),
            ("Passwordless authentication with FIDO2 hardware keys is the future of account security.", "Positive")
        ]
    },
    {
        "category": "Climate Action & Sustainability",
        "hashtags": ["#Sustainability", "#ClimateAction", "#CleanEnergy", "#ESG", "#GreenTech", "#SolarPower"],
        "posts": [
            ("Solar and wind power installations surpassed fossil fuel additions for the third consecutive year! ☀️🌱", "Positive"),
            ("Global temperatures hit another record high this month. Urgent structural climate policies are needed now.", "Negative"),
            ("Our corporate data centers just transitioned to 100% renewable energy contracts today.", "Positive"),
            ("Greenwashing remains rampant among Fortune 500 ESG marketing claims without independent audits.", "Negative"),
            ("New battery chemistries using sodium-ion show promising cost reductions for grid-scale energy storage.", "Positive"),
            ("Assessing the carbon footprint of training large-scale deep learning models in modern cloud centers.", "Neutral"),
            ("Severe droughts affecting hydroelectric output across several major regions this summer.", "Negative"),
            ("Excited to participate in the local coastal cleanup and biodiversity restoration project this weekend!", "Positive")
        ]
    },
    {
        "category": "Cloud Computing & DevOps",
        "hashtags": ["#CloudComputing", "#DevOps", "#Kubernetes", "#AWS", "#Docker", "#Microservices"],
        "posts": [
            ("Migrating monolithic architecture to Kubernetes microservices reduced our server bill by 35%. ☁️🚀", "Positive"),
            ("Major cloud provider outage in us-east-1 took down half our staging environments this afternoon.", "Negative"),
            ("Infrastructure as Code (Terraform) has transformed how our team manages multi-region deployments.", "Positive"),
            ("Troubleshooting distributed tracing across 40 microservices when latency spikes is a nightmare.", "Negative"),
            ("Continuous integration and automated testing pipelines are non-negotiable for high-velocity teams.", "Positive"),
            ("Comparing AWS, Azure, and Google Cloud pricing for high-throughput GPU workloads in 2026.", "Neutral"),
            ("Container security scanning caught three critical vulnerabilities before production rollout.", "Positive"),
            ("Unexpected egress charges on our monthly cloud invoice gave our finance team a heart attack.", "Negative")
        ]
    },
    {
        "category": "Fintech & Cryptocurrencies",
        "hashtags": ["#Fintech", "#Crypto", "#Blockchain", "#PersonalFinance", "#Web3", "#Investing"],
        "posts": [
            ("Instant cross-border payments with near-zero transaction fees are democratizing remittances worldwide. 💳", "Positive"),
            ("Market volatility triggers massive liquidations across speculative crypto derivative exchanges.", "Negative"),
            ("Decentralized identity protocols are solving real digital verification challenges in developing regions.", "Positive"),
            ("Regulatory crackdowns intensify as fraudulent investment schemes targeting retail investors proliferate.", "Negative"),
            ("Central Bank Digital Currencies (CBDCs) are entering pilot stages across 20+ countries this year.", "Neutral"),
            ("Automated dollar-cost averaging into index funds remains the most reliable long-term wealth strategy.", "Positive"),
            ("High transaction gas fees during peak network congestion make decentralized apps unusable for small trades.", "Negative")
        ]
    },
    {
        "category": "Health & Fitness",
        "hashtags": ["#HealthAndWellness", "#FitnessGoals", "#MentalHealth", "#Nutrition", "#HealthyLiving"],
        "posts": [
            ("Hit a new personal record on deadlifts today! Consistency and proper nutrition make all the difference. 🏋️‍♂️💪", "Positive"),
            ("Burnout is real. Prioritizing 8 hours of sleep and daily walking has restored my energy and focus.", "Positive"),
            ("Struggling with chronic back pain from poor sitting posture during long coding sessions.", "Negative"),
            ("Meal prepping balanced high-protein meals on Sunday saves both money and mental bandwidth during the week.", "Positive"),
            ("Too many influencers promote pseudoscience and dangerous restrictive diets with zero medical credentials.", "Negative"),
            ("Mindfulness meditation for 10 minutes every morning has visibly reduced my cortisol and anxiety levels.", "Positive"),
            ("Skipped workout today due to overwhelming fatigue. Listening to your body is just as important as training.", "Neutral")
        ]
    },
    {
        "category": "E-Commerce & Digital Marketing",
        "hashtags": ["#DigitalMarketing", "#Ecommerce", "#SocialMedia", "#ContentCreator", "#SEO", "#Branding"],
        "posts": [
            ("Our direct-to-consumer brand achieved 120% YoY revenue growth powered by authentic user-generated content! 📈", "Positive"),
            ("Ad customer acquisition costs on major platforms have doubled over the past 18 months.", "Negative"),
            ("Optimizing page load speed to under 1.5 seconds increased mobile checkout conversion by 18%.", "Positive"),
            ("Algorithm changes slashed organic reach overnight. Diversifying your audience into email lists is vital.", "Negative"),
            ("A/B testing email subject lines gave us a 42% open rate on our holiday announcement newsletter.", "Positive"),
            ("Analyzing audience demographics and engagement retention graphs to refine our Q3 content strategy.", "Neutral"),
            ("Customer service chatbot failed miserably on complex return inquiries, causing user frustration.", "Negative")
        ]
    }
]

platforms = ["Twitter/X", "Instagram", "LinkedIn", "Facebook"]
platform_weights = [0.42, 0.28, 0.20, 0.10]

users = [
    "alex_tech", "sarah_datasci", "code_ninja", "priya_dev", "michael_cloud", 
    "elena_ai", "david_crypto", "fitness_guru", "eco_warrior", "marketing_hub",
    "john_sec", "emily_travels", "rachel_ux", "carlos_biz", "ananya_ai",
    "kevin_sys", "lisa_health", "marcus_lead", "zack_devops", "maya_green"
]

start_date = datetime(2026, 8, 1)
end_date = datetime(2026, 11, 20)
date_range_days = (end_date - start_date).days

records = []
total_records = 1250

for i in range(1, total_records + 1):
    post_id = f"POST_{i:04d}"
    topic_item = random.choice(topics_data)
    topic_name = topic_item["category"]
    post_text, base_sentiment = random.choice(topic_item["posts"])
    
    # Select 2 to 4 hashtags from the category plus occasional general ones
    num_tags = random.randint(2, 4)
    selected_tags = random.sample(topic_item["hashtags"], min(num_tags, len(topic_item["hashtags"])))
    if random.random() < 0.3:
        selected_tags.append(random.choice(["#Trending", "#Viral", "#FYP", "#DailyUpdate"]))
    hashtags_str = " ".join(selected_tags)
    
    # Platform selection
    platform = random.choices(platforms, weights=platform_weights)[0]
    author = random.choice(users)
    
    # Timestamp generation with diurnal and temporal pattern
    random_days = random.randint(0, date_range_days)
    random_hours = random.choices(
        range(24),
        weights=[1, 1, 1, 1, 1, 2, 4, 6, 8, 9, 8, 7, 7, 8, 8, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    )[0]
    random_minutes = random.randint(0, 59)
    post_time = start_date + timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
    
    # Engagement generation (skewed / log-normal distribution)
    # Different platforms have typical engagement ranges
    if platform == "Twitter/X":
        likes = int(random.paretovariate(1.5) * 45)
        shares = int(likes * random.uniform(0.15, 0.45))
        comments = int(likes * random.uniform(0.05, 0.25))
    elif platform == "Instagram":
        likes = int(random.paretovariate(1.4) * 85)
        shares = int(likes * random.uniform(0.05, 0.20))
        comments = int(likes * random.uniform(0.08, 0.35))
    elif platform == "LinkedIn":
        likes = int(random.paretovariate(1.6) * 60)
        shares = int(likes * random.uniform(0.10, 0.30))
        comments = int(likes * random.uniform(0.12, 0.40))
    else: # Facebook
        likes = int(random.paretovariate(1.7) * 35)
        shares = int(likes * random.uniform(0.10, 0.25))
        comments = int(likes * random.uniform(0.05, 0.20))
        
    # Cap excessive extremes for realistic data
    likes = min(likes, 18500)
    shares = min(shares, 4200)
    comments = min(comments, 2100)
    
    # Add full post text combining text and hashtags
    full_content = f"{post_text} {hashtags_str}"
    
    records.append({
        "post_id": post_id,
        "author": author,
        "platform": platform,
        "post_content": full_content,
        "clean_content": post_text,
        "topic": topic_name,
        "hashtags": hashtags_str,
        "likes": likes,
        "shares": shares,
        "comments": comments,
        "sentiment": base_sentiment,
        "timestamp": post_time.strftime("%Y-%m-%d %H:%M:%S")
    })

# Add a few duplicates and slight missing value edge cases to demonstrate preprocessing module
# 15 duplicates
for dup in random.sample(records[:200], 15):
    records.append(dup.copy())

# Write out to dataset/social_media_data.csv
output_path = r"C:\Users\mirsh\.gemini\antigravity\scratch\Social_Media_Trend_Analysis\dataset\social_media_data.csv"

fieldnames = [
    "post_id", "author", "platform", "post_content", "topic",
    "hashtags", "likes", "shares", "comments", "sentiment", "timestamp"
]

with open(output_path, mode="w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in records:
        row = {k: r[k] for k in fieldnames}
        # Inject occasional missing hashtag or author to test missing value imputation
        if random.random() < 0.015:
            row["hashtags"] = ""
        writer.writerow(row)

print(f"Successfully generated {len(records)} records at {output_path}")
