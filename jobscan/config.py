"""JobScan configuration: lane definitions, company mapping, filter patterns."""
from __future__ import annotations

import re

LANES = [
    {
        "id": 1,
        "name": "Risk / Fraud / Payments / Onboarding Ops",
        "acceptable_titles": [
            "Risk Operations Analyst", "Payments Risk Analyst",
            "Fraud Analyst", "Fraud Operations Analyst",
            "Trust & Safety Analyst", "Trust and Safety Analyst",
            "Merchant Risk Analyst", "KYC Analyst",
            "Compliance Analyst", "AML Analyst",
            "Onboarding Analyst", "Identity Operations Analyst",
            "Disputes Analyst",
        ],
        "search_keywords": [
            "Fraud Analyst", "Risk Operations Analyst", "KYC Analyst",
            "AML Analyst", "Trust Safety Analyst", "Payments Risk Analyst",
            "Compliance Analyst", "Disputes Analyst", "Merchant Risk Analyst",
        ],
        "target_count": (6, 8),
    },
    {
        "id": 2,
        "name": "Operations-linked Data Analyst",
        "acceptable_titles": [
            "Data Analyst", "Operations Analyst",
            "Business Analyst", "Business Operations Analyst",
        ],
        "search_keywords": [
            "Data Analyst operations", "Data Analyst fraud",
            "Data Analyst trust", "Operations Analyst",
            "Business Analyst operations", "Business Operations Analyst",
        ],
        "exclude_titles": [
            "Product Analyst", "Growth Analyst", "Marketing Analyst",
        ],
        "target_count": (4, 5),
    },
    {
        "id": 3,
        "name": "AI Implementation / Solutions / Technical Ops",
        "acceptable_titles": [
            "Implementation Engineer", "Implementation Consultant",
            "Solutions Engineer", "Technical Success Engineer",
            "Customer Success Engineer", "Technical Operations Engineer",
            "AI Solutions Engineer", "Deployment Engineer",
            "Onboarding Engineer", "Professional Services Engineer",
        ],
        "search_keywords": [
            "Implementation Engineer AI", "Solutions Engineer AI",
            "Technical Success Engineer", "AI Solutions Engineer",
            "Deployment Engineer LLM", "Professional Services Engineer",
            "Implementation Consultant AI",
        ],
        "target_count": (3, 4),
    },
    {
        "id": 4,
        "name": "GTM Engineer",
        "acceptable_titles": [
            "GTM Engineer", "GTM Systems Engineer",
            "Revenue Operations Engineer", "Marketing Technologist",
            "Growth Engineer", "Sales Engineering Operations",
        ],
        "search_keywords": [
            "GTM Engineer", "Revenue Operations Engineer",
            "Marketing Technologist", "Growth Engineer sales",
            "GTM Systems Engineer",
        ],
        "target_count": (2, 3),
    },
]

PRIORITY_COMPANIES = [
    {"name": "Adyen", "ats": "greenhouse", "slug": "adyen"},
    {"name": "Owner.com", "ats": "unknown", "slug": "owner"},
    {"name": "Scribd", "ats": "greenhouse", "slug": "scribd"},
    {"name": "Airwallex", "ats": "greenhouse", "slug": "airwallex"},
    {"name": "Stripe", "ats": "greenhouse", "slug": "stripe"},
    {"name": "Square", "ats": "greenhouse", "slug": "squareup"},
    {"name": "Ramp", "ats": "greenhouse", "slug": "ramp"},
    {"name": "Mercury", "ats": "greenhouse", "slug": "mercury"},
    {"name": "Brex", "ats": "greenhouse", "slug": "brex"},
    {"name": "Plaid", "ats": "lever", "slug": "plaid"},
    {"name": "Chime", "ats": "greenhouse", "slug": "chime"},
    {"name": "Affirm", "ats": "greenhouse", "slug": "affirm"},
    {"name": "Marqeta", "ats": "greenhouse", "slug": "marqeta"},
    {"name": "ID.me", "ats": "greenhouse", "slug": "idme"},
    {"name": "Upgrade", "ats": "greenhouse", "slug": "upgrade"},
    {"name": "Cash App", "ats": "greenhouse", "slug": "cashapp"},
    {"name": "DoorDash", "ats": "greenhouse", "slug": "doordash"},
    {"name": "Instacart", "ats": "greenhouse", "slug": "instacart"},
    {"name": "Abridge", "ats": "greenhouse", "slug": "abridge"},
    {"name": "Fieldguide", "ats": "greenhouse", "slug": "fieldguide"},
    {"name": "Pinecone", "ats": "greenhouse", "slug": "pinecone"},
    {"name": "Swans", "ats": "unknown", "slug": "swans"},
    {"name": "Vooma", "ats": "unknown", "slug": "vooma"},
    {"name": "Alembic", "ats": "unknown", "slug": "alembic"},
    {"name": "Snorkel", "ats": "greenhouse", "slug": "snorkelai"},
    {"name": "Hex", "ats": "lever", "slug": "hex"},
    {"name": "Decagon", "ats": "ashby", "slug": "decagon"},
    {"name": "Dust", "ats": "unknown", "slug": "dust"},
    {"name": "Harper", "ats": "unknown", "slug": "harper"},
    {"name": "Revic", "ats": "unknown", "slug": "revic"},
    {"name": "Zyphra", "ats": "unknown", "slug": "zyphra"},
    {"name": "Deel", "ats": "greenhouse", "slug": "deel"},
    {"name": "Clay", "ats": "ashby", "slug": "clay"},
]

SENIORITY_PATTERN = (
    r"\b(?:Senior|Sr\.?|Staff|Principal|Lead|Manager|Director|VP|"
    r"Head\s+of|Chief\s+\w+\s+Officer|Chief)\b"
)

YOE_PATTERN = r"(?:[4-9]|[1-9]\d)\s*\\?\+?\s*(?:years?|yrs?)\b"

EXCLUDED_TITLES = [
    "Software Engineer",
    "ML Engineer",
    "Machine Learning Engineer",
    "Data Scientist",
    "Research Scientist",
    "Forward Deployed Engineer",
    "Applied Scientist",
    "Security Engineer",
    "DevOps Engineer",
    "Infrastructure Engineer",
    "Platform Engineer",
    "Site Reliability Engineer",
    "Backend Engineer",
    "Frontend Engineer",
    "Full-Stack Engineer",
    "Full Stack Engineer",
    "Fullstack Engineer",
    "Rust Engineer",
    "Cloud Engineer",
    "Network Engineer",
    "Hardware Engineer",
    "Electrical Engineer",
    "Mechanical Engineer",
    "Stationary Engineer",
    "Civil Engineer",
    "Chemical Engineer",
    "Behavior Technician",
    "Behavior Analyst",
    "Payroll Analyst",
    "Financial Analyst",
    "Accounting Analyst",
    "Tax Analyst",
    "Underwriter",
    "Actuary",
    "Nurse",
    "Physician",
    "Therapist",
    "Teacher",
    "Recruiter",
    "Designer",
    "Copywriter",
    "Content Writer",
    "AV Engineer",
    "IT Engineer",
    "Data Center Engineer",
    "Design Engineer",
    "Android Engineer",
    "iOS Engineer",
    "Mobile Engineer",
    "Research Engineer",
    "Account Executive",
    "Sales Development Representative",
    "SDR",
    "Business Development Representative",
    "BDR",
    "Customer Support",
    "Support Specialist",
    "Accountant",
    "Communications",
    "Comms",
    "Creative Technologist",
    "Production Support Engineer",
]

LOCATION_ALLOW_PATTERN = (
    r"(?:"
    r"San\s*Francisco|SF|Bay\s*Area|Oakland|San\s*Jose|Palo\s*Alto"
    r"|Mountain\s*View|Sunnyvale|Menlo\s*Park|Redwood\s*City|Santa\s*Clara"
    r"|Berkeley|Fremont|South\s*San\s*Francisco|Pleasanton|Dublin"
    r"|San\s*Mateo|Foster\s*City|Burlingame|Daly\s*City|Hayward|Livermore|Milpitas"
    r"|Remote|Anywhere|United\s*States|US\b|USA\b"
    r")"
)

PREF_STACK_LANES_12 = [
    "SQL", "Tableau", "Looker", "Snowflake", "Salesforce", "Sigma",
]

PREF_STACK_LANES_34 = [
    "Clay", "n8n", "Zapier", "Gumloop", "MCP", "Cursor",
    "Claude Code", "Claude", "Vertex AI", "OpenAI",
]
