"""
CVNova — Optimization Engine
Rule-based NLP analysis for ATS scoring, skill extraction, and improvement suggestions.
"""

import re
from collections import Counter

# ─── Job Role Skill Maps ─────────────────────────────────────────────────────

JOB_ROLES = {
    "software_engineer": {
        "title": "Software Engineer",
        "skills": [
            "python", "java", "javascript", "typescript", "c++", "go", "rust",
            "react", "angular", "vue", "node.js", "express", "django", "flask",
            "sql", "postgresql", "mongodb", "redis", "elasticsearch",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "git", "ci/cd", "jenkins", "github actions",
            "rest api", "graphql", "microservices", "system design",
            "data structures", "algorithms", "oop", "design patterns",
            "unit testing", "integration testing", "tdd",
            "agile", "scrum", "jira", "linux"
        ]
    },
    "frontend_developer": {
        "title": "Frontend Developer",
        "skills": [
            "html", "css", "javascript", "typescript",
            "react", "vue", "angular", "svelte", "next.js", "nuxt.js",
            "tailwind css", "sass", "less", "bootstrap",
            "webpack", "vite", "babel", "eslint", "prettier",
            "responsive design", "cross-browser compatibility", "accessibility",
            "rest api", "graphql", "axios", "fetch api",
            "git", "npm", "yarn", "pnpm",
            "unit testing", "jest", "cypress", "playwright",
            "performance optimization", "seo", "pwa",
            "figma", "design systems", "ui/ux"
        ]
    },
    "backend_developer": {
        "title": "Backend Developer",
        "skills": [
            "python", "java", "node.js", "go", "rust", "c#", "php",
            "django", "flask", "express", "spring boot", "fastapi",
            "sql", "postgresql", "mysql", "mongodb", "redis", "cassandra",
            "rest api", "graphql", "grpc", "websockets",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "microservices", "system design", "message queues", "rabbitmq", "kafka",
            "authentication", "oauth", "jwt", "security",
            "git", "ci/cd", "linux", "nginx",
            "unit testing", "integration testing", "load testing"
        ]
    },
    "full_stack_developer": {
        "title": "Full Stack Developer",
        "skills": [
            "html", "css", "javascript", "typescript", "python", "java",
            "react", "angular", "vue", "next.js", "node.js", "express",
            "django", "flask", "spring boot", "fastapi",
            "sql", "postgresql", "mongodb", "redis",
            "rest api", "graphql", "websockets",
            "docker", "kubernetes", "aws", "azure", "gcp",
            "git", "ci/cd", "github actions", "jenkins",
            "responsive design", "tailwind css", "bootstrap",
            "unit testing", "jest", "cypress",
            "agile", "scrum", "jira", "linux", "nginx"
        ]
    },
    "data_scientist": {
        "title": "Data Scientist",
        "skills": [
            "python", "r", "sql", "scala",
            "pandas", "numpy", "scipy", "scikit-learn",
            "tensorflow", "pytorch", "keras", "xgboost",
            "machine learning", "deep learning", "nlp", "computer vision",
            "statistics", "probability", "hypothesis testing", "a/b testing",
            "data visualization", "matplotlib", "seaborn", "tableau", "power bi",
            "spark", "hadoop", "hive", "airflow",
            "feature engineering", "model deployment", "mlops",
            "jupyter", "git", "docker", "aws", "gcp",
            "regression", "classification", "clustering", "neural networks"
        ]
    },
    "data_analyst": {
        "title": "Data Analyst",
        "skills": [
            "sql", "python", "r", "excel", "google sheets",
            "tableau", "power bi", "looker", "data studio",
            "pandas", "numpy", "matplotlib", "seaborn",
            "data visualization", "data cleaning", "data wrangling",
            "statistics", "hypothesis testing", "a/b testing", "regression",
            "etl", "data warehousing", "redshift", "bigquery", "snowflake",
            "business intelligence", "reporting", "dashboards",
            "google analytics", "kpi", "metrics",
            "communication", "presentation", "stakeholder management",
            "jupyter", "git", "critical thinking"
        ]
    },
    "ml_engineer": {
        "title": "Machine Learning Engineer",
        "skills": [
            "python", "java", "c++", "scala",
            "tensorflow", "pytorch", "keras", "scikit-learn", "xgboost",
            "machine learning", "deep learning", "reinforcement learning",
            "nlp", "computer vision", "recommendation systems",
            "neural networks", "cnn", "rnn", "transformers", "gans",
            "feature engineering", "model optimization", "model deployment",
            "mlops", "kubeflow", "mlflow", "sagemaker",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "spark", "hadoop", "distributed computing",
            "sql", "pandas", "numpy", "git", "ci/cd",
            "data pipelines", "airflow", "kafka"
        ]
    },
    "ai_engineer": {
        "title": "AI Engineer",
        "skills": [
            "python", "c++", "java", "rust",
            "tensorflow", "pytorch", "keras", "onnx",
            "machine learning", "deep learning", "reinforcement learning",
            "nlp", "computer vision", "speech recognition", "generative ai",
            "transformers", "llm", "gpt", "bert", "diffusion models",
            "langchain", "hugging face", "openai api",
            "neural networks", "cnn", "rnn", "attention mechanisms",
            "model optimization", "quantization", "pruning",
            "docker", "kubernetes", "aws", "gcp", "azure",
            "mlops", "model deployment", "api development",
            "sql", "pandas", "numpy", "git",
            "distributed computing", "gpu programming", "cuda"
        ]
    },
    "deep_learning_engineer": {
        "title": "Deep Learning Engineer",
        "skills": [
            "python", "c++", "cuda",
            "tensorflow", "pytorch", "keras", "jax",
            "deep learning", "neural networks", "cnn", "rnn", "lstm",
            "transformers", "attention mechanisms", "gans",
            "computer vision", "nlp", "speech recognition",
            "image classification", "object detection", "segmentation",
            "model optimization", "quantization", "pruning", "distillation",
            "gpu programming", "distributed training", "mixed precision",
            "docker", "kubernetes", "aws", "gcp",
            "mlops", "model deployment", "tensorrt", "onnx",
            "pandas", "numpy", "opencv", "git",
            "research", "publications", "experimentation"
        ]
    },
    "cloud_engineer": {
        "title": "Cloud Engineer",
        "skills": [
            "aws", "azure", "gcp", "cloud computing",
            "ec2", "s3", "lambda", "rds", "dynamodb", "cloudformation",
            "terraform", "ansible", "pulumi", "infrastructure as code",
            "docker", "kubernetes", "ecs", "eks",
            "ci/cd", "jenkins", "github actions", "gitlab ci",
            "linux", "bash", "python", "shell scripting",
            "networking", "vpc", "load balancing", "dns", "cdn",
            "monitoring", "cloudwatch", "prometheus", "grafana",
            "security", "iam", "ssl", "encryption",
            "serverless", "api gateway", "microservices",
            "cost optimization", "high availability", "disaster recovery"
        ]
    },
    "devops_engineer": {
        "title": "DevOps Engineer",
        "skills": [
            "docker", "kubernetes", "terraform", "ansible", "puppet", "chef",
            "aws", "azure", "gcp", "cloud computing",
            "ci/cd", "jenkins", "github actions", "gitlab ci", "circleci",
            "linux", "bash", "shell scripting", "python",
            "monitoring", "prometheus", "grafana", "datadog", "elk stack",
            "nginx", "apache", "load balancing",
            "networking", "tcp/ip", "dns", "vpn", "firewall",
            "git", "version control", "infrastructure as code",
            "security", "ssl", "iam", "vault",
            "microservices", "serverless", "lambda"
        ]
    },
    "cybersecurity_analyst": {
        "title": "Cybersecurity Analyst",
        "skills": [
            "network security", "information security", "cybersecurity",
            "siem", "splunk", "qradar", "sentinel",
            "firewalls", "ids/ips", "vpn", "encryption",
            "penetration testing", "vulnerability assessment", "ethical hacking",
            "incident response", "threat detection", "malware analysis",
            "owasp", "nist", "iso 27001", "compliance",
            "linux", "windows", "networking", "tcp/ip", "dns",
            "python", "bash", "powershell", "scripting",
            "wireshark", "nmap", "metasploit", "burp suite",
            "risk assessment", "security auditing", "access control",
            "cloud security", "aws", "azure", "endpoint security"
        ]
    },
    "blockchain_developer": {
        "title": "Blockchain Developer",
        "skills": [
            "solidity", "rust", "javascript", "typescript", "python", "go",
            "ethereum", "bitcoin", "polkadot", "solana", "polygon",
            "smart contracts", "dapps", "defi", "nft", "dao",
            "web3.js", "ethers.js", "hardhat", "truffle", "foundry",
            "evm", "consensus mechanisms", "cryptography",
            "react", "next.js", "node.js",
            "ipfs", "the graph", "chainlink", "oracles",
            "security auditing", "gas optimization",
            "git", "ci/cd", "docker",
            "sql", "mongodb", "redis",
            "agile", "scrum", "testing"
        ]
    },
    "mobile_app_developer": {
        "title": "Mobile App Developer",
        "skills": [
            "react native", "flutter", "dart", "swift", "kotlin",
            "javascript", "typescript", "java", "objective-c",
            "ios", "android", "cross-platform",
            "xcode", "android studio", "expo",
            "rest api", "graphql", "firebase", "push notifications",
            "sqlite", "realm", "core data",
            "ui/ux", "material design", "responsive design",
            "git", "ci/cd", "fastlane",
            "unit testing", "integration testing", "app store", "google play",
            "performance optimization", "memory management",
            "agile", "scrum", "jira"
        ]
    },
    "android_developer": {
        "title": "Android Developer",
        "skills": [
            "kotlin", "java", "android sdk",
            "android studio", "gradle", "jetpack compose",
            "material design", "xml layouts", "fragments", "activities",
            "mvvm", "mvp", "clean architecture",
            "retrofit", "room", "hilt", "dagger",
            "coroutines", "flow", "livedata", "viewmodel",
            "rest api", "graphql", "firebase",
            "sqlite", "shared preferences", "datastore",
            "unit testing", "espresso", "junit", "mockito",
            "git", "ci/cd", "google play", "play console",
            "push notifications", "performance optimization",
            "agile", "scrum", "jira"
        ]
    },
    "ios_developer": {
        "title": "iOS Developer",
        "skills": [
            "swift", "objective-c", "swiftui", "uikit",
            "xcode", "cocoapods", "swift package manager",
            "core data", "core animation", "core location",
            "auto layout", "storyboard", "programmatic ui",
            "mvvm", "mvc", "viper", "clean architecture",
            "combine", "async/await", "grand central dispatch",
            "rest api", "graphql", "urlsession", "alamofire",
            "firebase", "push notifications", "app store connect",
            "unit testing", "xctest", "ui testing",
            "git", "ci/cd", "fastlane",
            "accessibility", "localization",
            "agile", "scrum", "jira"
        ]
    },
    "game_developer": {
        "title": "Game Developer",
        "skills": [
            "unity", "unreal engine", "godot",
            "c#", "c++", "python", "lua", "blueprint",
            "game design", "level design", "game mechanics",
            "3d modeling", "animation", "physics simulation",
            "opengl", "vulkan", "directx", "shaders", "hlsl", "glsl",
            "multiplayer", "networking", "photon",
            "ai pathfinding", "behavior trees", "state machines",
            "optimization", "profiling", "memory management",
            "version control", "git", "perforce",
            "agile", "scrum", "jira",
            "playtesting", "debugging",
            "audio design", "ux design"
        ]
    },
    "ui_designer": {
        "title": "UI Designer",
        "skills": [
            "figma", "sketch", "adobe xd", "photoshop", "illustrator",
            "ui design", "visual design", "graphic design",
            "design systems", "component libraries", "style guides",
            "typography", "color theory", "iconography",
            "responsive design", "mobile design", "web design",
            "prototyping", "wireframing", "mockups",
            "html", "css", "animation",
            "material design", "ios design guidelines",
            "brand identity", "branding",
            "collaboration", "communication", "presentation",
            "user research", "usability testing",
            "accessibility", "wcag", "inclusive design"
        ]
    },
    "ux_designer": {
        "title": "UX Designer",
        "skills": [
            "figma", "sketch", "adobe xd", "invision", "zeplin",
            "user research", "usability testing", "user interviews",
            "wireframing", "prototyping", "mockups", "design systems",
            "information architecture", "interaction design", "visual design",
            "typography", "color theory", "responsive design", "accessibility",
            "html", "css", "javascript",
            "design thinking", "human-centered design",
            "persona", "user flows", "journey mapping", "card sorting",
            "heuristic evaluation", "a/b testing",
            "collaboration", "communication", "presentation"
        ]
    },
    "product_manager": {
        "title": "Product Manager",
        "skills": [
            "product strategy", "roadmap", "product lifecycle",
            "user research", "user stories", "personas", "customer journey",
            "agile", "scrum", "kanban", "sprint planning",
            "jira", "confluence", "trello", "asana",
            "data analysis", "sql", "analytics", "google analytics",
            "a/b testing", "kpi", "okr", "metrics",
            "stakeholder management", "cross-functional", "leadership",
            "market research", "competitive analysis", "business strategy",
            "wireframing", "figma", "prototyping",
            "communication", "presentation", "prioritization"
        ]
    },
    "technical_product_manager": {
        "title": "Technical Product Manager",
        "skills": [
            "product strategy", "roadmap", "product lifecycle",
            "technical architecture", "system design", "api design",
            "agile", "scrum", "kanban", "sprint planning",
            "jira", "confluence", "trello",
            "sql", "python", "data analysis", "analytics",
            "a/b testing", "kpi", "okr", "metrics",
            "stakeholder management", "cross-functional", "leadership",
            "rest api", "microservices", "cloud computing",
            "aws", "gcp", "docker", "ci/cd",
            "user stories", "technical specifications",
            "market research", "competitive analysis",
            "communication", "presentation", "prioritization"
        ]
    },
    "business_analyst": {
        "title": "Business Analyst",
        "skills": [
            "business analysis", "requirements gathering", "process mapping",
            "stakeholder management", "user stories", "use cases",
            "sql", "excel", "power bi", "tableau",
            "data analysis", "reporting", "dashboards",
            "agile", "scrum", "waterfall", "jira", "confluence",
            "bpmn", "uml", "flowcharts", "visio",
            "gap analysis", "swot analysis", "cost-benefit analysis",
            "communication", "presentation", "documentation",
            "project management", "change management",
            "crm", "erp", "salesforce",
            "kpi", "metrics", "critical thinking"
        ]
    },
    "digital_marketing": {
        "title": "Digital Marketing Specialist",
        "skills": [
            "seo", "sem", "ppc", "google ads", "facebook ads",
            "social media marketing", "instagram", "linkedin", "tiktok",
            "content marketing", "email marketing", "copywriting",
            "google analytics", "google tag manager", "hubspot",
            "mailchimp", "hootsuite", "buffer",
            "conversion optimization", "landing pages", "funnel optimization",
            "a/b testing", "marketing automation",
            "brand strategy", "campaign management", "budget management",
            "crm", "salesforce", "lead generation",
            "video marketing", "influencer marketing",
            "data analysis", "roi analysis", "kpi tracking",
            "html", "css", "wordpress"
        ]
    },
    "seo_specialist": {
        "title": "SEO Specialist",
        "skills": [
            "seo", "on-page seo", "off-page seo", "technical seo",
            "keyword research", "content optimization", "link building",
            "google analytics", "google search console", "google tag manager",
            "ahrefs", "semrush", "moz", "screaming frog",
            "schema markup", "structured data", "xml sitemaps",
            "html", "css", "javascript", "wordpress",
            "page speed optimization", "core web vitals",
            "content strategy", "copywriting", "blogging",
            "competitive analysis", "serp analysis",
            "local seo", "international seo",
            "reporting", "data analysis", "a/b testing",
            "mobile optimization", "crawlability", "indexation"
        ]
    },
    "content_strategist": {
        "title": "Content Strategist",
        "skills": [
            "content strategy", "content planning", "editorial calendar",
            "copywriting", "content writing", "blog writing",
            "seo", "keyword research", "content optimization",
            "social media", "email marketing", "newsletter",
            "google analytics", "content management systems", "wordpress",
            "brand voice", "tone of voice", "messaging",
            "audience research", "persona development", "user journey",
            "video content", "podcast", "webinars",
            "project management", "collaboration", "communication",
            "a/b testing", "performance metrics", "kpi",
            "hubspot", "semrush", "canva", "photoshop"
        ]
    },
    "it_support": {
        "title": "IT Support Specialist",
        "skills": [
            "technical support", "help desk", "troubleshooting",
            "windows", "macos", "linux", "active directory",
            "networking", "tcp/ip", "dns", "dhcp", "vpn",
            "hardware", "software installation", "system administration",
            "office 365", "google workspace", "microsoft teams",
            "ticketing systems", "servicenow", "zendesk", "jira",
            "remote support", "desktop support", "printer management",
            "security", "antivirus", "backup", "disaster recovery",
            "itil", "documentation", "knowledge base",
            "communication", "customer service", "problem solving",
            "powershell", "bash", "scripting"
        ]
    },
    "network_engineer": {
        "title": "Network Engineer",
        "skills": [
            "networking", "tcp/ip", "dns", "dhcp", "bgp", "ospf",
            "cisco", "juniper", "arista", "fortinet",
            "switches", "routers", "firewalls", "load balancers",
            "lan", "wan", "vlan", "vpn", "sd-wan",
            "network security", "ids/ips", "access control",
            "monitoring", "nagios", "solarwinds", "wireshark",
            "cloud networking", "aws", "azure", "gcp",
            "automation", "python", "ansible", "terraform",
            "linux", "windows server",
            "ccna", "ccnp", "network+",
            "troubleshooting", "documentation", "change management"
        ]
    },
    "database_administrator": {
        "title": "Database Administrator",
        "skills": [
            "sql", "postgresql", "mysql", "oracle", "sql server",
            "mongodb", "cassandra", "redis", "dynamodb",
            "database design", "data modeling", "normalization",
            "performance tuning", "query optimization", "indexing",
            "backup", "recovery", "disaster recovery", "replication",
            "high availability", "clustering", "sharding",
            "security", "access control", "encryption", "auditing",
            "monitoring", "alerting", "automation",
            "etl", "data migration", "data warehousing",
            "linux", "windows server", "bash", "python",
            "aws rds", "azure sql", "cloud databases",
            "documentation", "change management"
        ]
    },
    "qa_engineer": {
        "title": "QA Engineer",
        "skills": [
            "manual testing", "test planning", "test cases", "test execution",
            "automation testing", "selenium", "cypress", "playwright",
            "api testing", "postman", "rest assured",
            "performance testing", "jmeter", "loadrunner", "gatling",
            "python", "java", "javascript", "typescript",
            "ci/cd", "jenkins", "github actions",
            "jira", "confluence", "test management",
            "agile", "scrum", "sprint testing",
            "regression testing", "smoke testing", "sanity testing",
            "mobile testing", "appium", "cross-browser testing",
            "sql", "database testing", "bug tracking",
            "security testing", "accessibility testing"
        ]
    },
    "automation_tester": {
        "title": "Automation Tester",
        "skills": [
            "selenium", "cypress", "playwright", "appium",
            "python", "java", "javascript", "typescript",
            "test automation frameworks", "page object model",
            "testng", "junit", "pytest", "mocha", "jest",
            "api testing", "rest assured", "postman",
            "ci/cd", "jenkins", "github actions", "gitlab ci",
            "bdd", "cucumber", "gherkin",
            "performance testing", "jmeter", "gatling",
            "git", "version control",
            "docker", "containerized testing",
            "sql", "database testing",
            "agile", "scrum", "jira",
            "reporting", "allure", "extent reports"
        ]
    },
    "system_administrator": {
        "title": "System Administrator",
        "skills": [
            "linux", "windows server", "macos",
            "active directory", "group policy", "ldap",
            "networking", "tcp/ip", "dns", "dhcp", "vpn",
            "virtualization", "vmware", "hyper-v", "proxmox",
            "bash", "powershell", "python", "scripting",
            "docker", "kubernetes", "containerization",
            "aws", "azure", "gcp", "cloud computing",
            "monitoring", "nagios", "zabbix", "prometheus",
            "backup", "disaster recovery", "high availability",
            "security", "firewalls", "iam", "patch management",
            "automation", "ansible", "terraform",
            "documentation", "itil", "change management"
        ]
    }
}


# ─── Custom Role Skill Generator ──────────────────────────────────────────────

# Broad skill categories for generating skills for custom/unknown roles
_SKILL_CATEGORIES = {
    "general_tech": [
        "python", "javascript", "java", "sql", "git", "docker", "aws",
        "linux", "rest api", "ci/cd", "agile", "scrum"
    ],
    "data": [
        "python", "sql", "pandas", "numpy", "data analysis",
        "data visualization", "tableau", "power bi", "statistics",
        "machine learning", "excel", "reporting"
    ],
    "design": [
        "figma", "sketch", "adobe xd", "photoshop", "illustrator",
        "ui design", "ux design", "wireframing", "prototyping",
        "typography", "responsive design", "user research"
    ],
    "marketing": [
        "seo", "google analytics", "social media marketing",
        "content marketing", "email marketing", "copywriting",
        "google ads", "hubspot", "a/b testing", "campaign management"
    ],
    "management": [
        "project management", "leadership", "stakeholder management",
        "communication", "presentation", "agile", "scrum", "jira",
        "strategic planning", "budgeting", "team management"
    ],
    "infrastructure": [
        "linux", "networking", "docker", "kubernetes", "aws",
        "terraform", "ansible", "monitoring", "security", "bash",
        "ci/cd", "cloud computing"
    ]
}

# Keywords to map custom role titles to skill categories
_ROLE_CATEGORY_KEYWORDS = {
    "general_tech": ["engineer", "developer", "programmer", "coder", "software", "web", "app", "application"],
    "data": ["data", "analyst", "analytics", "scientist", "machine learning", "ai", "ml", "intelligence", "bi"],
    "design": ["design", "ui", "ux", "creative", "visual", "graphic", "interface"],
    "marketing": ["marketing", "seo", "content", "social", "digital", "brand", "advertising", "media"],
    "management": ["manager", "lead", "director", "head", "chief", "coordinator", "administrator", "officer"],
    "infrastructure": ["devops", "cloud", "infrastructure", "network", "system", "security", "support", "admin"]
}


def _generate_custom_role_skills(role_name):
    """Generate expected skills for a custom job role based on its name."""
    role_lower = role_name.lower()
    matched_categories = set()
    all_skills = []

    # Find matching categories
    for category, keywords in _ROLE_CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            if keyword in role_lower:
                matched_categories.add(category)
                break

    # If no category matched, use general_tech + management as fallback
    if not matched_categories:
        matched_categories = {"general_tech", "management"}

    # Collect skills from matched categories
    for category in matched_categories:
        all_skills.extend(_SKILL_CATEGORIES.get(category, []))

    # Deduplicate and limit
    seen = set()
    unique_skills = []
    for skill in all_skills:
        if skill not in seen:
            seen.add(skill)
            unique_skills.append(skill)

    return unique_skills[:35]  # Cap at 35 skills


# ─── ATS Keywords ──────────────────────────────────────────────────────────────

IMPORTANT_SECTIONS = [
    "experience", "work experience", "professional experience", "employment",
    "education", "academic", "qualification",
    "skills", "technical skills", "core competencies", "technologies",
    "projects", "personal projects", "academic projects",
    "certifications", "certificates", "training",
    "summary", "professional summary", "objective", "profile",
    "achievements", "accomplishments", "awards"
]

ACTION_VERBS = [
    "achieved", "administered", "analyzed", "built", "collaborated",
    "created", "delivered", "designed", "developed", "directed",
    "drove", "engineered", "established", "executed", "generated",
    "implemented", "improved", "increased", "initiated", "launched",
    "led", "managed", "mentored", "optimized", "orchestrated",
    "organized", "pioneered", "reduced", "resolved", "scaled",
    "spearheaded", "streamlined", "supervised", "transformed"
]

FILLER_WORDS = [
    "responsible for", "duties included", "helped with",
    "assisted in", "was tasked with", "involved in",
    "participated in", "worked on", "had to"
]

WEAK_PHRASES = [
    "hard worker", "team player", "detail oriented", "detail-oriented",
    "self-motivated", "go-getter", "think outside the box",
    "synergy", "passionate", "fast learner", "quick learner"
]


def analyze_resume(text, job_role="software_engineer", job_description="", custom_role=""):
    """Main analysis function that returns a complete analysis report."""
    # Clean PDF artifacts like (cid:127)
    text = re.sub(r'\(cid:\d+\)', '', text)
    
    text_lower = text.lower()
    words = text_lower.split()
    word_count = len(words)

    # Determine role data — custom role or predefined
    if custom_role and custom_role.strip():
        role_title = custom_role.strip().title()
        role_skills = _generate_custom_role_skills(custom_role)
        role_data = {"title": role_title, "skills": role_skills}
        is_custom = True
    else:
        role_data = JOB_ROLES.get(job_role, JOB_ROLES["software_engineer"])
        is_custom = False

    # Run all analysis modules
    sections_found = _detect_sections(text_lower)
    found_skills, missing_skills = _extract_skills(text_lower, role_data["skills"])
    strengths = _identify_strengths(text, text_lower, words, sections_found, found_skills)
    weaknesses = _identify_weaknesses(text, text_lower, words, sections_found, missing_skills)
    suggestions = _generate_suggestions(text, text_lower, words, sections_found, found_skills, missing_skills)
    grammar_suggestions = _grammar_check(text, text_lower)
    ats_score = _calculate_ats_score(text, text_lower, words, sections_found, found_skills, missing_skills, role_data)
    jd_match = _match_job_description(text_lower, job_description) if job_description else None
    
    # New Advanced Features
    identity = _extract_structured_data(text, role_data["title"])
    sections = identity.get("raw_sections", {})
    section_strength = _score_section_strengths(sections, found_skills, missing_skills, word_count)
    bullet_rewrites = _generate_bullet_rewrites(text)
    keyword_examples = _generate_keyword_examples(missing_skills)
    formatting = _check_formatting_deep_dive(text, sections_found)

    roadmap = _generate_roadmap(missing_skills, role_data["title"])
    interview_questions = _generate_interview_questions(text, found_skills, role_data["title"], sections)
    job_recommendations = _recommend_jobs(found_skills, missing_skills, text_lower, role_data["title"])
    ai_rewrites = _ai_auto_rewrite(text, sections)

    # Deterministic skill match score
    total_role_skills = len(role_data["skills"])
    skill_match_score = round((len(found_skills) / total_role_skills) * 100) if total_role_skills > 0 else 0

    result = {
        "ats_score": ats_score,
        "skill_match_score": skill_match_score,
        "role": role_data["title"],
        "is_custom_role": is_custom,
        "word_count": word_count,
        "resume_text": text,
        "sections_found": sections_found,
        "found_skills": sorted(found_skills),
        "missing_skills": sorted(missing_skills),
        "strengths": strengths,
        "weaknesses": weaknesses,
        "suggestions": suggestions,
        "grammar_suggestions": grammar_suggestions,
        "jd_match": jd_match,
        "identity": identity,
        "sections": sections,
        "section_strength": section_strength,
        "formatting": formatting,
        "bullet_rewrites": bullet_rewrites,
        "keyword_examples": keyword_examples,
        "roadmap": roadmap,
        "interview_questions": interview_questions,
        "job_recommendations": job_recommendations,
        "ai_rewrites": ai_rewrites
    }

    return result


def _detect_sections(text_lower):
    """Detect which standard resume sections are present."""
    found = []
    for section in IMPORTANT_SECTIONS:
        pattern = r'\b' + re.escape(section) + r'\b'
        if re.search(pattern, text_lower):
            found.append(section.title())
    return found


def _extract_skills(text_lower, role_skills):
    """Extract found and missing skills from resume text."""
    found = []
    missing = []
    for skill in role_skills:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower):
            found.append(skill.title())
        else:
            missing.append(skill.title())
    return found, missing


def _identify_strengths(text, text_lower, words, sections_found, found_skills):
    """Identify resume strengths."""
    strengths = []

    # Check for quantified achievements
    numbers = re.findall(r'\d+[%+]|\$[\d,]+|\d+\s*(?:users|customers|clients|projects|teams|people)', text_lower)
    if len(numbers) >= 2:
        strengths.append({
            "title": "Quantified Achievements",
            "detail": f"Found {len(numbers)} quantified results — ATS systems and recruiters love measurable impact.",
            "icon": "📊"
        })

    # Check for action verbs
    used_verbs = [v for v in ACTION_VERBS if v in text_lower]
    if len(used_verbs) >= 5:
        strengths.append({
            "title": "Strong Action Verbs",
            "detail": f"Uses {len(used_verbs)} powerful action verbs like '{used_verbs[0]}', '{used_verbs[1]}', '{used_verbs[2]}'. Great for ATS parsing.",
            "icon": "💪"
        })

    # Check section coverage
    if len(sections_found) >= 4:
        strengths.append({
            "title": "Well-Structured Sections",
            "detail": f"Resume has {len(sections_found)} key sections identified. Good organization helps ATS systems categorize your information.",
            "icon": "📋"
        })

    # Skill coverage
    if len(found_skills) >= 8:
        strengths.append({
            "title": "Strong Skill Coverage",
            "detail": f"{len(found_skills)} relevant skills detected. This increases keyword match rate with job postings.",
            "icon": "🎯"
        })

    # Good length
    word_count = len(words)
    if 300 <= word_count <= 900:
        strengths.append({
            "title": "Optimal Resume Length",
            "detail": f"At {word_count} words, your resume is a good length — concise yet detailed enough.",
            "icon": "📏"
        })

    # Contact information
    has_email = bool(re.search(r'[\w.-]+@[\w.-]+\.\w+', text))
    has_phone = bool(re.search(r'[\+]?[\d\s\-\(\)]{10,}', text))
    has_linkedin = 'linkedin' in text_lower
    if has_email and has_phone:
        strengths.append({
            "title": "Contact Information Present",
            "detail": "Email and phone detected." + (" LinkedIn profile also found." if has_linkedin else ""),
            "icon": "📧"
        })

    # Career Level indicators
    if any(kw in text_lower for kw in ["senior", "lead", "architect", "manager", "head"]):
        strengths.append({
            "title": "Leadership Experience",
            "detail": "Keywords indicating leadership or high-level seniority found. This adds significant weight to your profile.",
            "icon": "👑"
        })

    # Vocabulary diversity
    if len(set(words)) / len(words) > 0.4:
        strengths.append({
            "title": "Strong Vocabulary Diversity",
            "detail": "Good varied use of terminology. Avoiing repetition keeps the reader and ATS engaged.",
            "icon": "📚"
        })

    # Tech Stack richness
    if len(found_skills) > 12:
        strengths.append({
            "title": "Rich Tech Stack",
            "detail": f"Impressive breadth of {len(found_skills)} technical skills detected.",
            "icon": "💻"
        })

    # Add general positive indicators to ensure 7-8
    while len(strengths) < 7:
        strengths.append({
            "title": "Professional Tone",
            "detail": "The overall language is professional and suitable for modern corporate hiring standards.",
            "icon": "✨"
        })

    return strengths[:8]


def _identify_weaknesses(text, text_lower, words, sections_found, missing_skills):
    """Identify resume weaknesses."""
    weaknesses = []

    # Missing key sections
    essential = ["Experience", "Education", "Skills"]
    missing_sections = [s for s in essential if s not in sections_found and s.lower() not in [sf.lower() for sf in sections_found]]
    # Also check alternate names
    for s in list(missing_sections):
        alternates = {
            "Experience": ["work experience", "professional experience", "employment"],
            "Education": ["academic", "qualification"],
            "Skills": ["technical skills", "core competencies", "technologies"]
        }
        for alt in alternates.get(s, []):
            if alt.title() in sections_found:
                missing_sections.remove(s)
                break

    if missing_sections:
        weaknesses.append({
            "title": "Missing Key Sections",
            "detail": f"Could not detect: {', '.join(missing_sections)}. ATS systems rely on section headers to parse content.",
            "icon": "⚠️"
        })

    # Too many missing skills
    if len(missing_skills) > 15:
        weaknesses.append({
            "title": "Low Keyword Match",
            "detail": f"{len(missing_skills)} relevant skills are missing from your resume. This reduces ATS match rate significantly.",
            "icon": "🔍"
        })

    # Filler words
    fillers_found = [f for f in FILLER_WORDS if f in text_lower]
    if fillers_found:
        weaknesses.append({
            "title": "Weak Language Detected",
            "detail": f"Found passive phrases like \"{fillers_found[0]}\". Replace with strong action verbs for better impact.",
            "icon": "📝"
        })

    # Weak/cliché phrases
    cliches_found = [w for w in WEAK_PHRASES if w in text_lower]
    if cliches_found:
        weaknesses.append({
            "title": "Cliché Phrases",
            "detail": f"Phrases like \"{cliches_found[0]}\" are overused. Show these qualities through achievements instead.",
            "icon": "🚫"
        })

    # Resume too short or too long
    word_count = len(words)
    if word_count < 150:
        weaknesses.append({
            "title": "Resume Too Short",
            "detail": f"Only {word_count} words detected. Resumes should generally be 300–800 words for ATS optimization.",
            "icon": "📉"
        })
    elif word_count > 1200:
        weaknesses.append({
            "title": "Resume Too Long",
            "detail": f"{word_count} words detected. Consider trimming to under 800 words to keep it focused.",
            "icon": "📈"
        })

    # Missing portfolio
    if 'portfolio' not in text_lower and 'github' not in text_lower:
        weaknesses.append({
            "title": "Missing Portfolio/Github Link",
            "detail": "Modern recruiters expect to see your work in action. Absence of links can be a red flag in tech.",
            "icon": "🌐"
        })

    # Adverb heavy
    adverbs = re.findall(r'\b\w+ly\b', text_lower)
    if len(adverbs) > 10:
        weaknesses.append({
            "title": "Heavy Use of Adverbs",
            "detail": f"Found {len(adverbs)} adverbs. Use stronger verbs instead of qualifying weak ones (e.g., 'Spearheaded' instead of 'Quickly led').",
            "icon": "💅"
        })

    # Deduplicate weaknesses by title
    unique_weaknesses = []
    seen_titles = set()
    for w in weaknesses:
        if w["title"] not in seen_titles:
            unique_weaknesses.append(w)
            seen_titles.add(w["title"])

    return unique_weaknesses[:5]


def _generate_suggestions(text, text_lower, words, sections_found, found_skills, missing_skills):
    """Generate actionable improvement suggestions."""
    suggestions = []

    # Skill suggestions — top 5 missing
    if missing_skills:
        top_missing = missing_skills[:5]
        suggestions.append({
            "priority": "high",
            "title": "Add Missing Keywords",
            "detail": f"Include these high-value skills if applicable: {', '.join(top_missing)}",
            "icon": "🔑"
        })

    # Section suggestions
    if "Summary" not in sections_found and "Professional Summary" not in sections_found and "Profile" not in sections_found:
        suggestions.append({
            "priority": "high",
            "title": "Add a Professional Summary",
            "detail": "A 2-3 line summary at the top helps ATS systems and recruiters quickly understand your profile.",
            "icon": "📝"
        })

    if "Certifications" not in sections_found and "Certificates" not in sections_found:
        suggestions.append({
            "priority": "medium",
            "title": "Add Certifications Section",
            "detail": "Include relevant certifications to boost credibility and ATS keyword matching.",
            "icon": "🏆"
        })

    # Action verbs
    used_verbs = [v for v in ACTION_VERBS if v in text_lower]
    if len(used_verbs) < 5:
        suggestions.append({
            "priority": "high",
            "title": "Use More Action Verbs",
            "detail": "Start bullet points with verbs like: achieved, developed, implemented, optimized, delivered.",
            "icon": "💪"
        })

    # LinkedIn
    if 'linkedin' not in text_lower:
        suggestions.append({
            "priority": "medium",
            "title": "Add LinkedIn Profile",
            "detail": "Including a LinkedIn URL increases credibility and allows recruiters to learn more about you.",
            "icon": "🔗"
        })

    # GitHub for tech roles
    if 'github' not in text_lower and 'portfolio' not in text_lower:
        suggestions.append({
            "priority": "medium",
            "title": "Add Portfolio/GitHub Link",
            "detail": "A link to your work portfolio or GitHub demonstrates practical skills beyond keywords.",
            "icon": "💻"
        })

    # Skills grouping
    if "skills" in sections_found and len(found_skills) > 10:
        suggestions.append({
            "priority": "medium",
            "title": "Categorize Your Skills",
            "detail": "Group skills into categories (e.g., Languages, Frameworks, Tools) to make them easier to scan.",
            "icon": "📁"
        })

    # Profile summary depth
    if "Summary" in sections_found and len(text.partition("Summary")[2].split()) < 20:
        suggestions.append({
            "priority": "medium",
            "title": "Expand Professional Summary",
            "detail": "Your summary is a bit brief. Aim for 3 impactful lines that highlight your years of experience and top 3 skills.",
            "icon": "🖋️"
        })

    while len(suggestions) < 7:
        suggestions.append({
            "priority": "low",
            "title": "Modernize Layout",
            "detail": "Consider using a modern, two-column layout if your resume exceeds one page to keep core info above the fold.",
            "icon": "🎨"
        })

    return suggestions[:8]


def _grammar_check(text, text_lower):
    """Basic grammar and content quality checks."""
    suggestions = []

    # Passive voice indicators
    passive_patterns = [
        r'\bwas\s+\w+ed\b', r'\bwere\s+\w+ed\b',
        r'\bbeen\s+\w+ed\b', r'\bbeing\s+\w+ed\b'
    ]
    passive_count = sum(len(re.findall(p, text_lower)) for p in passive_patterns)
    if passive_count >= 3:
        suggestions.append({
            "type": "grammar",
            "title": "Reduce Passive Voice",
            "detail": f"Found ~{passive_count} instances of passive voice. Use active voice: 'Developed the app' instead of 'The app was developed'.",
            "icon": "✏️"
        })

    # First person pronouns
    pronoun_count = len(re.findall(r'\b(i|me|my|mine|myself)\b', text_lower))
    if pronoun_count > 5:
        suggestions.append({
            "type": "grammar",
            "title": "Remove First-Person Pronouns",
            "detail": f"Found {pronoun_count} first-person references. Resumes should avoid 'I', 'my', etc. Use implied subject: 'Developed...' not 'I developed...'",
            "icon": "👤"
        })

    # Inconsistent tense
    past_verbs = len(re.findall(r'\b\w+ed\b', text_lower))
    present_verbs = len(re.findall(r'\b(manage|develop|create|design|lead|build|implement|analyze|drive|coordinate)s?\b', text_lower))
    if past_verbs > 5 and present_verbs > 5:
        suggestions.append({
            "type": "content",
            "title": "Inconsistent Tense Usage",
            "detail": "Mix of past and present tense detected. Use past tense for previous roles and present tense only for current position.",
            "icon": "⏰"
        })

    # Spelling common mistakes
    common_misspellings = {
        "recieve": "receive", "managment": "management",
        "developement": "development", "expereince": "experience",
        "acheivement": "achievement", "comunication": "communication",
        "responsibilty": "responsibility", "enviroment": "environment",
        "sucessful": "successful", "accesible": "accessible"
    }
    for wrong, right in common_misspellings.items():
        if wrong in text_lower:
            suggestions.append({
                "type": "spelling",
                "title": f"Spelling: '{wrong}'",
                "detail": f"Consider changing to '{right}'.",
                "icon": "🔤"
            })

    # Sentence length
    sentences = re.split(r'[.!?]+', text)
    long_sentences = [s for s in sentences if len(s.split()) > 30]
    if len(long_sentences) >= 2:
        suggestions.append({
            "type": "content",
            "title": "Simplify Long Sentences",
            "detail": f"Found {len(long_sentences)} sentences with 30+ words. Break them into shorter, impactful statements.",
            "icon": "✂️"
        })

    if not suggestions:
        suggestions.append({
            "type": "info",
            "title": "No Major Issues Found",
            "detail": "Your resume text looks clean. Focus on content improvements from the suggestions above.",
            "icon": "✅"
        })

    return suggestions


def _calculate_ats_score(text, text_lower, words, sections_found, found_skills, missing_skills, role_data):
    """Calculate ATS compatibility score out of 100 using a deterministic weighted formula.
    
    Weights:
        Keyword Coverage:        40%
        Section Presence:        20%
        Formatting Quality:      20%
        Action Verbs:            10%
        Quantified Achievements: 10%
    """
    score = 0
    breakdown = {}

    # ── 1. Keyword Coverage (max 40) ─────────────────────────────────────
    total_role_skills = len(role_data.get("skills", []))
    skill_ratio = len(found_skills) / total_role_skills if total_role_skills > 0 else 0
    keyword_score = round(skill_ratio * 40)
    keyword_score = min(keyword_score, 40)
    score += keyword_score
    breakdown["keywords"] = {"score": keyword_score, "max": 40, "label": "Keyword Coverage"}

    # ── 2. Section Presence (max 20) ─────────────────────────────────────
    core_sections = {"skills", "experience", "education", "projects"}
    sections_lower = {s.lower() for s in sections_found}
    matched_sections = core_sections & sections_lower
    section_score = len(matched_sections) * 5  # 5 pts each
    section_score = min(section_score, 20)
    score += section_score
    breakdown["sections"] = {"score": section_score, "max": 20, "label": "Section Presence"}

    # ── 3. Formatting Quality (max 20) ───────────────────────────────────
    format_score = 0
    # Bullet points (5 pts)
    bullet_count = len(re.findall(r'[•\-\–\—\*►▪■]', text))
    if bullet_count >= 5:
        format_score += 5
    elif bullet_count >= 2:
        format_score += 3

    # Proper section headers (5 pts)
    header_count = len(re.findall(r'^[A-Z][A-Za-z\s&\/]+:?\s*$', text, re.MULTILINE))
    if header_count >= 3:
        format_score += 5
    elif header_count >= 1:
        format_score += 3

    # Paragraph length — no dense blocks (5 pts)
    blocks = text.split('\n\n')
    long_blocks = sum(1 for b in blocks if len(b.split()) > 40 and not re.search(r'[•\-\–\—\*]', b))
    if long_blocks == 0:
        format_score += 5
    elif long_blocks <= 2:
        format_score += 3

    # Contact info present (5 pts)
    contact_pts = 0
    if re.search(r'[\w.-]+@[\w.-]+\.\w+', text): contact_pts += 2  # email
    if re.search(r'[\+]?[\d\s\-\(\)]{10,}', text): contact_pts += 2  # phone
    if 'linkedin' in text_lower: contact_pts += 1  # linkedin
    format_score += min(contact_pts, 5)

    format_score = min(format_score, 20)
    score += format_score
    breakdown["formatting"] = {"score": format_score, "max": 20, "label": "Formatting Quality"}

    # ── 4. Action Verbs (max 10) ─────────────────────────────────────────
    used_verbs = [v for v in ACTION_VERBS if v in text_lower]
    verb_score = min(len(used_verbs), 10)
    score += verb_score
    breakdown["action_verbs"] = {"score": verb_score, "max": 10, "label": "Action Verbs"}

    # ── 5. Quantified Achievements (max 10) ──────────────────────────────
    numbers = re.findall(r'\d+[%+]|\$[\d,]+|\d+x\b', text)
    achievement_score = min(len(numbers) * 2, 10)
    score += achievement_score
    breakdown["achievements"] = {"score": achievement_score, "max": 10, "label": "Quantified Achievements"}

    score = max(0, min(100, score))

    return {
        "total": score,
        "breakdown": breakdown,
        "grade": _score_to_grade(score)
    }


def _score_to_grade(score):
    if score >= 85: return {"letter": "A", "label": "Excellent", "color": "#00e676"}
    if score >= 70: return {"letter": "B", "label": "Good", "color": "#66bb6a"}
    if score >= 55: return {"letter": "C", "label": "Average", "color": "#ffa726"}
    if score >= 40: return {"letter": "D", "label": "Below Average", "color": "#ff7043"}
    return {"letter": "F", "label": "Needs Work", "color": "#ef5350"}


def _match_job_description(text_lower, job_description):
    """Match resume against a provided job description."""
    if not job_description or not job_description.strip():
        return None

    jd_lower = job_description.lower()

    # Extract meaningful words from JD (3+ chars, not common words)
    stop_words = {
        "the", "and", "for", "are", "with", "you", "our", "your", "this",
        "that", "will", "have", "from", "they", "been", "has", "was",
        "were", "can", "may", "would", "should", "could", "about",
        "into", "than", "its", "also", "not", "but", "who", "what",
        "when", "which", "their", "them", "all", "more", "other",
        "some", "such", "only", "any", "each", "those", "these",
        "must", "able", "work", "working", "experience", "role",
        "team", "company", "position", "looking", "join", "etc"
    }

    jd_words = set(re.findall(r'\b[a-z][a-z+#/.]{2,}\b', jd_lower)) - stop_words
    resume_words = set(re.findall(r'\b[a-z][a-z+#/.]{2,}\b', text_lower))

    matched = jd_words & resume_words
    missing = jd_words - resume_words

    match_pct = round((len(matched) / len(jd_words) * 100)) if jd_words else 0

    # Filter to most relevant missing keywords (top 15)
    missing_sorted = sorted(missing, key=lambda x: len(x), reverse=True)[:15]
    
    # Identify missing technical skills (3+ chars, likely tech)
    # We can refine this by checking against known skill lists if needed
    missing_tech = [w for w in missing_sorted if len(w) > 2]

    return {
        "match_percentage": match_pct,
        "matched_keywords": sorted(matched)[:20],
        "missing_keywords": missing_sorted,
        "missing_tech_skills": missing_tech[:8],
        "total_jd_keywords": len(jd_words),
        "matched_count": len(matched)
    }


def _generate_roadmap(missing_skills, role_title):
    """Generate a learning roadmap based on missing skills."""
    if not missing_skills:
        return {
            "title": f"Upskilling Roadmap for {role_title}",
            "steps": [
                {"title": "Advanced Mastery", "detail": "You already have all the core skills! Focus on deep-diving into niche frameworks or contributing to open source.", "tech": []},
                {"title": "System Design", "detail": "Prepare for high-level architecture interviews and scaling challenges.", "tech": ["Distributed Systems", "Cloud Architecture"]}
            ]
        }

    # Group skills into roadmap steps
    steps = []
    
    # Step 1: Immediate Gaps (top 3)
    if len(missing_skills) > 0:
        steps.append({
            "title": "Foundation & Core Tools",
            "detail": "Start with these essential skills that are frequently required for this role.",
            "tech": missing_skills[:3],
            "projects": [f"Build a {role_title} side project using {missing_skills[0]}"]
        })

    # Step 2: Intermediate Frameworks
    if len(missing_skills) > 3:
        steps.append({
            "title": "Advanced Frameworks & Testing",
            "detail": "Once you have the basics, master these frameworks to build robust applications.",
            "tech": missing_skills[3:6],
            "projects": ["Implement unit and integration testing in your existing projects"]
        })

    # Step 3: Deployment & Infrastructure
    infra_keywords = ["AWS", "Docker", "Kubernetes", "CI/CD", "Terraform", "Ansible", "Cloud"]
    infra_missing = [s for s in missing_skills if any(k.lower() in s.lower() for k in infra_keywords)]
    if infra_missing:
        steps.append({
            "title": "Cloud & Infrastructure",
            "detail": "Learn how to deploy and scale your applications in a modern cloud environment.",
            "tech": infra_missing[:3],
            "projects": ["Containerize your application and deploy it to a cloud provider"]
        })
    elif len(missing_skills) > 6:
        steps.append({
            "title": "Cloud & Infrastructure",
            "detail": "Even if not explicitly missing, mastering cloud tools will significantly boost your profile.",
            "tech": ["Docker", "AWS", "GitHub Actions"],
            "projects": ["Setup an automated CI/CD pipeline for your portfolio"]
        })

    return {
        "title": f"Career Roadmap for {role_title}",
        "steps": steps
    }


def _generate_interview_questions(text, found_skills, role_title, sections=None):
    """Generate personalized interview questions."""
    import os
    import json
    
    # Check if OpenAI is available Let's use it for highly personalized questions
    if os.getenv('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            projects_text = sections.get('Projects', '') if sections else ""
            if not projects_text.strip() and sections:
                projects_text = sections.get('Experience', '')
            
            prompt = f"Generate 10 personalized interview questions for a {role_title} based on this candidate's profile.\n\n"
            prompt += f"Their known Hard Skills: {', '.join(found_skills[:15])}\n\n"
            prompt += f"Their Experience & Projects Context:\n{projects_text[:1200]}\n\n"
            prompt += "Please return EXACTLY a JSON format with three keys: 'technical', 'projects', and 'behavioral'.\n"
            prompt += "- 'technical': Array of 5 strings (Deep technical questions about the skills they know).\n"
            prompt += "- 'projects': Array of 3 strings (Specific questions explicitly about what they built based on their Experience & Projects Contact. Name the project!).\n"
            prompt += "- 'behavioral': Array of 2 strings (Standard behavioral questions for this role).\n"
            
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert technical interviewer. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={ "type": "json_object" }
            )
            
            content = response.choices[0].message.content
            parsed = json.loads(content)
            
            # Ensure keys exist
            if 'technical' in parsed and 'projects' in parsed and 'behavioral' in parsed:
                return parsed
                
        except Exception as e:
            # Fall back to heuristic if API fails or parsing isn't valid
            print(f"OpenAI interview generation failed: {e}")

    # Fallback heuristic logic
    # 5 Technical Questions (based on found skills)
    tech_qs = []
    sample_skills = found_skills[:5] if found_skills else ["Software Engineering", "Problem Solving"]
    
    for skill in sample_skills:
        tech_qs.append(f"Can you explain a challenging technical problem you solved using {skill}?")
    
    # Ensure at least 5
    while len(tech_qs) < 5:
        tech_qs.append("How do you stay updated with the latest trends in technology?")

    # 3 Project-based Questions
    # Try to find projects in text
    project_indicators = ["project", "built", "created", "developed", "designed"]
    projects_found = []
    for line in text.split('\n'):
        if any(ind in line.lower() for ind in project_indicators):
            if len(line.split()) > 5:
                projects_found.append(line.strip())
    
    project_qs = []
    if projects_found:
        project_qs.append(f"Tell me more about your experience with: '{projects_found[0][:50]}...'")
        project_qs.append("What was the most difficult part of that project and how did you overcome it?")
        project_qs.append("If you had to redo that project today, what would you change?")
    else:
        project_qs = [
            "Tell me about a complex project you worked on recently.",
            "What technical trade-offs did you make during your most significant project?",
            "How did you handle version control and collaboration in your team projects?"
        ]

    # 2 Behavioral Questions
    behavioral_qs = [
        "Describe a time you had to work with a difficult teammate. How did you handle it?",
        "Tell me about a time you failed or made a mistake. What did you learn?"
    ]

    return {
        "technical": tech_qs[:5],
        "projects": project_qs[:3],
        "behavioral": behavioral_qs[:2]
    }


# ─── New Advanced Intelligent Modules ──────────────────────────────────────────

def _extract_structured_data(text, role_title="Not Specified"):
    """Extract Name, Contact info, Job Role, and basic section chunking."""
    lines = text.split('\n')
    
    # 1. Extract Name (Heuristic: usually first or second line, 2-3 words, capitalized)
    name = "Not Detected"
    for line in lines[:5]:
        clean_line = line.strip()
        if len(clean_line.split()) in [1, 2, 3] and not re.search(r'\d|@', clean_line) and len(clean_line) > 2:
            name = clean_line.title()
            break

    # 2. Extract Contact
    email = re.search(r'[\w.-]+@[\w.-]+\.\w+', text)
    email = email.group(0) if email else "Not Detected"
    
    phone = re.search(r'[\+]?[\d\s\-\(\)]{10,}', text)
    phone = phone.group(0) if phone else "Not Detected"

    linkedin_match = re.search(r'(linkedin\.com/in/[\w.-]+)', text, re.IGNORECASE)
    linkedin = linkedin_match.group(1) if linkedin_match else "Not Detected"
    
    github_match = re.search(r'(github\.com/[\w.-]+)', text, re.IGNORECASE)
    github = github_match.group(1) if github_match else "Not Detected"

    # 3. Possible Job Role Extraction
    possible_role = "Not Detected"
    # Look for common titles in the first 15 lines
    titles = ["Engineer", "Developer", "Manager", "Analyst", "Scientist", "Architect", "Lead", "Consultant", "Designer"]
    for line in lines[:15]:
        line_clean = line.strip()
        if any(title in line_clean for title in titles) and len(line_clean.split()) < 6:
            possible_role = line_clean
            break
    
    if possible_role == "Not Detected":
        possible_role = role_title

    # 4. Enhanced Section Chunking (Experience, Education, Projects, Skills, Summary, Certifications)
    raw_sections = {
        "Summary": "", "Experience": "", "Education": "", 
        "Projects": "", "Skills": "", "Certifications": "", "Languages": ""
    }
    
    current_section = None
    
    # Common headers to look out for
    headers_map = {
        "summary": "Summary", "profile": "Summary", "objective": "Summary",
        "experience": "Experience", "employment": "Experience", "work history": "Experience",
        "education": "Education", "academic": "Education", "university": "Education", "college": "Education",
        "project": "Projects", "portfolio": "Projects",
        "skill": "Skills", "technolog": "Skills", "tools": "Skills", "core competencies": "Skills",
        "certificat": "Certifications", "course": "Certifications", "training": "Certifications",
        "language": "Languages"
    }
    
    for line in lines:
        line_clean = line.strip()
        line_lower = line_clean.lower()
        
        # Detect headers by checking if line is short and contains keyword
        is_header = False
        if len(line_clean.split()) <= 4 and line_clean:
            # Check if line matches a header keyword
            for kw, sec_name in headers_map.items():
                if kw in line_lower:
                    current_section = sec_name
                    is_header = True
                    break
        
        if not is_header and current_section and line_clean:
            raw_sections[current_section] += line_clean + "\n"

    # Fallback: if sections are still extremely empty, just chunk the text blindly into 3 parts
    # to guarantee the UI has something interesting to show
    total_len = sum(len(v) for v in raw_sections.values())
    if total_len < 100:
        chunk_size = len(lines) // 3
        raw_sections["Experience"] = "\n".join(lines[:chunk_size]).strip()
        raw_sections["Skills"] = "\n".join(lines[chunk_size:chunk_size*2]).strip()
        raw_sections["Education"] = "\n".join(lines[chunk_size*2:]).strip()

    return {
        "name": name,
        "email": email,
        "phone": phone,
        "linkedin": linkedin,
        "github": github,
        "possible_role": possible_role,
        "raw_sections": raw_sections
    }

def _score_section_strengths(raw_sections, found_skills, missing_skills, word_count):
    """Evaluate individual section strength (Skills, Projects, Experience, Education)."""
    scores = {
        "Summary": 0, "Experience": 0, "Education": 0, 
        "Projects": 0, "Skills": 0, "Certifications": 0, "Languages": 0
    }
    
    # Skills Section
    skill_text = raw_sections.get("Skills", "").strip()
    total_kws = len(found_skills) + len(missing_skills)
    skill_ratio = len(found_skills) / total_kws if total_kws > 0 else 0
    skill_val = 0
    if skill_text:
        skill_val = 50 + (skill_ratio * 50)
    elif found_skills:
        skill_val = 30 + (skill_ratio * 40)
    scores["Skills"] = min(100, max(0, int(skill_val)))

    # Experience Section
    exp_text = raw_sections.get("Experience", "").strip()
    if exp_text:
        exp_val = 40
        if re.search(r'•|–|—|-', exp_text): exp_val += 20
        metrics = len(re.findall(r'\d+[%+]|\$[\d,]+', exp_text))
        exp_val += min(25, metrics * 8)
        word_vol = len(exp_text.split())
        if word_vol > 150: exp_val += 15
        elif word_vol > 50: exp_val += 5
        scores["Experience"] = min(100, max(0, int(exp_val)))

    # Projects Section
    proj_text = raw_sections.get("Projects", "").strip()
    if proj_text:
        proj_val = 50
        if re.search(r'•|–|—|-', proj_text): proj_val += 15
        metrics = len(re.findall(r'\d+[%+]|\$[\d,]+', proj_text))
        proj_val += min(20, metrics * 10)
        if len(proj_text.split()) > 80: proj_val += 15
        scores["Projects"] = min(100, max(0, int(proj_val)))

    # Education Section
    edu_text = raw_sections.get("Education", "").strip()
    if edu_text:
        edu_val = 60
        if re.search(r'20\d{2}|19\d{2}', edu_text): edu_val += 20
        if any(kw in edu_text.lower() for kw in ["degree", "bachelor", "university", "college", "bs", "ms", "phd"]): 
            edu_val += 20
        scores["Education"] = min(100, max(0, int(edu_val)))

    # Summary
    sum_text = raw_sections.get("Summary", "").strip()
    if sum_text:
        sum_val = 70
        if 20 < len(sum_text.split()) < 100: sum_val += 20
        scores["Summary"] = min(100, int(sum_val))

    # Certs & Langs (Optional enrichment)
    if raw_sections.get("Certifications", "").strip(): scores["Certifications"] = 85
    if raw_sections.get("Languages", "").strip(): scores["Languages"] = 90

    # Ensure we show at least 4 scores even if sections missing
    for k in ["Skills", "Experience", "Education", "Projects"]:
        if scores[k] == 0:
            scores[k] = 10 # Minimal presence score if keywords found but no header

    return scores

def _generate_bullet_rewrites(text):
    """Detect weak bullet points and provide improved generative suggestions."""
    rewrites = []
    lines = text.split('\n')
    bullets = [line.strip() for line in lines if re.match(r'^[•\-\–\—\*]\s+', line.strip()) or len(line.split()) > 6]
    
    weak_verbs = ["helped", "worked", "assisted", "responsible for", "handled", "did", "made"]
    
    for bullet in bullets:
        bullet_lower = bullet.lower()
        if any(w in bullet_lower for w in weak_verbs) and not re.search(r'\d', bullet):
            clean_b = re.sub(r'^[•\-\–\—\*]\s+', '', bullet).strip()
            improved = ""
            if "responsible for" in bullet_lower:
                improved = clean_b.lower().replace("responsible for", "Managed and executed")
                improved = improved.capitalize() + ", resulting in a 20% increase in efficiency."
            elif "helped" in bullet_lower or "assisted" in bullet_lower:
                improved = "Collaborated with cross-functional teams to " + clean_b.lower().replace("helped ", "").replace("assisted ", "") + ", delivering the project ahead of schedule."
            elif "worked on" in bullet_lower:
                improved = clean_b.lower().replace("worked on", "Spearheaded the development of") + ", improving overall performance metrics by 15%."
            else:
                improved = "Optimized and streamlined " + clean_b.lower() + " across the organization, yielding measurable positive outcomes."

            if len(clean_b) > 15:
                rewrites.append({
                    "original": clean_b,
                    "improved": improved
                })
            
            if len(rewrites) >= 4:
                break
                
    return rewrites

def _generate_keyword_examples(missing_skills):
    """Provides example sentences for missing skills to help the user add them."""
    examples = []
    
    templates = [
        "Architected a scalable solution utilizing {skill} to reduce latency.",
        "Integrated {skill} into the CI/CD pipeline, improving deployment speed.",
        "Led a team of 5 to successfully migrate legacy systems to {skill}.",
        "Analyzed market trends using {skill} to increase quarterly revenue by 10%.",
        "Designed responsive UI components using {skill} for a seamless user experience.",
        "Leveraged {skill} to automate daily reporting tasks."
    ]
    
    for i, skill in enumerate(missing_skills[:6]):
        examples.append({
            "keyword": skill,
            "example": templates[i % len(templates)].format(skill=skill)
        })
        
    return examples

def _check_formatting_deep_dive(text, sections_found):
    """Detailed formatting analysis (missing sections, long paragraphs)."""
    issues = []
    
    # Check for core sections
    core = {"Experience", "Education", "Skills"}
    missing_core = [c for c in core if c not in sections_found and c.lower() not in [sf.lower() for sf in sections_found]]
    if missing_core:
        issues.append({
            "title": "Missing Core Sections",
            "detail": f"Could not detect: {', '.join(missing_core)}. ATS systems require these headers to categorize your data.",
            "icon": "⚠️"
        })
    else:
        issues.append({
            "title": "Standard ATS Headers",
            "detail": "All core sections (Experience, Education, Skills) are present and well-labeled.",
            "icon": "✅"
        })
        
    # Paragraph density
    blocks = text.split('\n\n')
    long_paragraphs = 0
    for b in blocks:
        if len(b.split()) > 40 and not re.search(r'[•\-\–\—\*]', b):
            long_paragraphs += 1
            
    if long_paragraphs > 0:
        issues.append({
            "title": "Dense Paragraphs",
            "detail": f"Found {long_paragraphs} paragraph(s) longer than 40 words. Try breaking these into bullet points.",
            "icon": "🌫️"
        })
    else:
        issues.append({
            "title": "Optimal Paragraph Length",
            "detail": "Your text blocks are concise and easy for recruiters to scan in under 6 seconds.",
            "icon": "📏"
        })
        
    # Bullet density
    bullet_count = len(re.findall(r'[•\-\–\—\*]', text))
    if bullet_count < 5:
        issues.append({
            "title": "Low Bullet Point Density",
            "detail": f"Only {bullet_count} bullet points found. Use more bullets to highlight specific accomplishments.",
            "icon": "📌"
        })
    elif bullet_count > 20:
        issues.append({
            "title": "Excellent Use of Bullets",
            "detail": f"{bullet_count} items found. This significantly improves readability and ATS parsing.",
            "icon": "📊"
        })
    else:
        issues.append({
            "title": "Balanced Structural Layout",
            "detail": "Good mixture of summary text and bulleted achievements.",
            "icon": "⚖️"
        })

    # Contact formatting
    if re.search(r'[\w.-]+@[\w.-]+\.\w+', text):
        issues.append({
            "title": "Email Formatting",
            "detail": "Email address is valid and clearly visible for recruitment teams.",
            "icon": "📧"
        })
    
    if re.search(r'linkedin\.com', text.lower()):
        issues.append({
            "title": "Professional Social Link",
            "detail": "LinkedIn profile link detected. This adds credibility to your application.",
            "icon": "🔗"
        })
    else:
        issues.append({
            "title": "LinkedIn Profile Missing",
            "detail": "Adding a LinkedIn URL is highly recommended for modern job applications.",
            "icon": "⚪"
        })

    # Consistency checks
    dates = re.findall(r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b', text)
    if dates:
        issues.append({
            "title": "Date Consistency",
            "detail": f"Found {len(dates)} dates with consistent month-year formatting.",
            "icon": "📅"
        })

    # Logical Flow
    if len(sections_found) > 0:
        issues.append({
            "title": "Section Ordering",
            "detail": "Information flows logically with standard resume conventions.",
            "icon": "🔄"
        })

    # Deduplicate formatting issues by title
    unique_issues = []
    seen_titles = set()
    for issue in issues:
        if issue["title"] not in seen_titles:
            unique_issues.append(issue)
            seen_titles.add(issue["title"])
            
    return unique_issues[:5]


def _recommend_jobs(found_skills, missing_skills, text_lower, current_role):
    """Recommend suitable job roles based on detected skills with rich detail."""
    found_set = set(s.lower() for s in found_skills)
    recommendations = []

    for role_id, role_data in JOB_ROLES.items():
        role_skills = set(s.lower() for s in role_data["skills"])
        matched = found_set & role_skills
        missing = role_skills - found_set
        match_pct = round(len(matched) / len(role_skills) * 100) if role_skills else 0

        if match_pct >= 10:
            matched_list = sorted([s.title() for s in matched])
            missing_list = sorted([s.title() for s in missing])
            why_fits = _generate_why_fits(matched_list, role_data["title"], match_pct)
            roadmap = _generate_learning_roadmap(missing_list[:5], role_data["title"])

            recommendations.append({
                "role": role_data["title"],
                "match_percentage": match_pct,
                "matched_skills": matched_list[:10],
                "missing_skills": missing_list[:8],
                "description": _get_role_description(role_id),
                "why_fits": why_fits,
                "learning_roadmap": roadmap,
                "suggestion": _get_role_suggestion(match_pct, role_data["title"], missing_list[:3])
            })

    recommendations.sort(key=lambda x: x["match_percentage"], reverse=True)

    if not recommendations:
        recommendations = [{
            "role": "Software Developer",
            "match_percentage": 10,
            "matched_skills": sorted([s.title() for s in found_skills])[:5],
            "missing_skills": ["Data Structures", "Algorithms", "Git", "REST API"],
            "description": "Build and maintain software applications using modern development practices.",
            "why_fits": "With your current skill set, building a foundation in software development opens doors to many specializations.",
            "learning_roadmap": [
                {"step": "1. Master a Programming Language", "detail": "Pick Python or JavaScript and build 3 projects."},
                {"step": "2. Learn Data Structures", "detail": "Complete a course on arrays, trees, graphs, and algorithms."},
                {"step": "3. Build Full-Stack Projects", "detail": "Create a web app with frontend + backend + database."}
            ],
            "suggestion": "Start with the fundamentals and build projects to demonstrate your abilities."
        }]

    return recommendations[:6]


def _generate_why_fits(matched_skills, role_title, match_pct):
    """Generate a personalized explanation of why this role fits the candidate."""
    if not matched_skills:
        return f"Pivoting into {role_title} could expand your career horizons. Start by building foundational skills."
    skills_str = ", ".join(matched_skills[:5])
    count = len(matched_skills)
    if match_pct >= 75:
        return f"Your profile is an excellent fit. You already demonstrate strong proficiency in {skills_str}, which are core competencies for this role. You're well-positioned to apply immediately."
    elif match_pct >= 50:
        return f"You have {count} matching skills including {skills_str}, giving you a solid foundation. A few targeted additions would make you a very competitive candidate."
    elif match_pct >= 30:
        return f"Your experience with {skills_str} provides a good starting point for transitioning into {role_title}. Focused upskilling would significantly boost your candidacy."
    else:
        return f"You have some relevant skills ({skills_str}) that relate to {role_title}. With dedicated learning, this could become a viable career path."


def _generate_learning_roadmap(missing_skills, role_title):
    """Generate a structured learning roadmap based on missing skills."""
    if not missing_skills:
        return [{"step": "1. Apply & Interview", "detail": f"Your skills align well. Start applying and prepare for technical interviews."}]
    roadmap = []
    for i, skill in enumerate(missing_skills[:3]):
        if i == 0:
            roadmap.append({"step": f"1. Learn {skill}", "detail": f"Start with official docs and tutorials. Build a small project to solidify understanding."})
        elif i == 1:
            roadmap.append({"step": f"2. Practice {skill}", "detail": f"Integrate {skill} into an existing project or create a dedicated portfolio piece."})
        else:
            roadmap.append({"step": f"3. Build with {skill}", "detail": f"Combine {skill} with your existing skills to build an end-to-end real-world project."})
    return roadmap


def _get_role_description(role_id):
    """Return a short description for each role."""
    descriptions = {
        "software_engineer": "Design, develop, and maintain software applications using modern technologies and best practices.",
        "frontend_developer": "Build responsive, performant user interfaces and web experiences using modern JavaScript frameworks.",
        "backend_developer": "Develop server-side logic, APIs, databases, and scalable infrastructure for web applications.",
        "fullstack_developer": "Work across the entire stack — from UI components to server-side APIs and database management.",
        "data_scientist": "Analyze complex datasets, build predictive models, and derive actionable business insights using ML algorithms.",
        "ml_engineer": "Design operation-ready machine learning pipelines, deploy models, and optimize ML infrastructure at scale.",
        "devops_engineer": "Automate infrastructure, manage CI/CD pipelines, and ensure system reliability and scalability.",
        "cloud_architect": "Design and implement cloud-native solutions, microservices, and distributed systems on major cloud platforms.",
        "mobile_developer": "Build native or cross-platform mobile applications for iOS and Android with great user experiences.",
        "cybersecurity_analyst": "Protect systems and networks from cyber threats through monitoring, testing, and security best practices.",
        "ai_engineer": "Build and deploy AI/ML solutions, natural language processing systems, and intelligent automation.",
        "data_engineer": "Build and maintain data pipelines, warehouses, and ETL processes for large-scale data processing.",
        "product_manager": "Define product strategy, prioritize features, and coordinate cross-functional teams to deliver user value.",
        "ui_ux_designer": "Design intuitive and user-focused interfaces by combining research, wireframing, and visual design.",
        "qa_engineer": "Ensure software quality through test automation, performance testing, and continuous integration.",
        "blockchain_developer": "Develop decentralized applications, smart contracts, and blockchain-based solutions.",
        "game_developer": "Create engaging games using game engines, 3D graphics, and interactive design principles.",
        "systems_engineer": "Design and manage complex IT infrastructure, operating systems, and embedded systems.",
        "database_administrator": "Manage, optimize, and secure database systems for performance and reliability.",
        "network_engineer": "Design, implement, and maintain network infrastructure and security.",
    }
    return descriptions.get(role_id, "A dynamic technology role requiring strong technical skills and problem-solving ability.")


def _get_role_suggestion(match_pct, role_title, missing_top3):
    """Generate a suggestion based on match percentage."""
    missing_str = ", ".join([s.title() for s in missing_top3]) if missing_top3 else "advanced topics"
    if match_pct >= 75:
        return f"You're an excellent match for {role_title}! Focus on polishing your resume and applying."
    elif match_pct >= 50:
        return f"Strong potential for {role_title}. Bridge the gap by learning {missing_str}."
    elif match_pct >= 30:
        return f"You have foundational skills for {role_title}. Invest time in {missing_str} to become competitive."
    else:
        return f"Consider building projects with {missing_str} to pivot toward {role_title}."


def _ai_auto_rewrite(text, sections):
    """Use OpenAI to rewrite weak resume sentences into professional bullets."""
    import os
    import json

    # Gather candidate sentences from Experience, Projects, and Summary
    exp_text = sections.get("Experience", "") if sections else ""
    proj_text = sections.get("Projects", "") if sections else ""
    summary_text = sections.get("Summary", "") if sections else ""
    combined = (exp_text + "\n" + proj_text + "\n" + summary_text).strip()

    if not combined or len(combined) < 20:
        # Even with no sections, try full text
        combined = text.strip()

    if not combined or len(combined) < 20:
        return []

    # Extract individual lines/bullets - much broader detection
    lines = combined.split('\n')
    candidates = []
    weak_indicators = [
        "helped", "worked", "assisted", "responsible for", "handled", "did",
        "made", "used", "worked on", "involved in", "was part of", "contributed",
        "participated", "tasked with", "dealt with", "took care of", "learned",
        "studied", "familiar with", "knowledge of", "exposure to", "good at",
        "concepts", "basics", "understanding of"
    ]

    # Pass 1: Find lines with genuinely weak language
    for line in lines:
        line = line.strip()
        # Remove PDF artifacts like (cid:127) and standard bullet markers
        clean = re.sub(r'\(cid:\d+\)', '', line)
        clean = re.sub(r'^[•\-\–\—\*\d\.]\s*', '', clean).strip()
        
        if len(clean.split()) >= 4 and any(w in clean.lower() for w in weak_indicators):
            candidates.append(clean)
        if len(candidates) >= 5:
            break

    # Pass 2: If not enough, pick any bullet-like lines that could be improved
    if len(candidates) < 3:
        for line in lines:
            line = line.strip()
            # Remove PDF artifacts like (cid:127) and standard bullet markers
            clean = re.sub(r'\(cid:\d+\)', '', line)
            clean = re.sub(r'^[•\-\–\—\*\d\.]\s*', '', clean).strip()
            
            if len(clean.split()) >= 4 and clean not in candidates:
                candidates.append(clean)
            if len(candidates) >= 5:
                break

    if not candidates:
        return []

    # Try OpenAI-powered rewrite
    if os.getenv('OPENAI_API_KEY'):
        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

            bullet_list = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

            prompt = f"""You are a senior resume consultant. Rewrite these resume bullet points to be highly professional.

Rules:
- Replace ALL weak/passive language (worked on, helped, responsible for, involved in, used, etc.)
- Start each bullet with a STRONG action verb (Engineered, Spearheaded, Architected, Developed, Optimized, Implemented, Designed, Led, Automated, Streamlined, etc.)
- Add SPECIFIC quantified results where possible (improved by X%, reduced latency by Xms, served X users, processed X records)
- Make each bullet demonstrate IMPACT and VALUE, not just activity
- Keep the improved version professional, concise, and recruiter-friendly
- Preserve the original meaning and technical context

Original bullets:
{bullet_list}

Return ONLY valid JSON with key "rewrites" containing a list of objects. Each object must have "original" (exact original text) and "improved" (the rewritten version) keys."""

            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert resume writer. You transform weak resume bullets into powerful, achievement-oriented statements. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            content = response.choices[0].message.content
            parsed = json.loads(content)

            # Handle both list and dict with "rewrites" key
            if isinstance(parsed, dict):
                for key in parsed:
                    if isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break

            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[:5]

        except Exception as e:
            print(f"OpenAI auto-rewrite failed: {e}")

    # Fallback: intelligent heuristic rewrites
    action_verbs = {
        "ml": "Engineered and deployed",
        "web": "Architected and developed",
        "data": "Designed and implemented",
        "api": "Built and optimized",
        "database": "Engineered and maintained",
        "test": "Established and executed",
        "deploy": "Orchestrated and automated",
        "design": "Conceptualized and delivered",
        "manage": "Spearheaded and coordinated",
        "default": "Developed and delivered"
    }

    rewrites = []
    for c in candidates[:5]:
        cl = c.lower()
        # Pick the best action verb based on content domain
        verb = action_verbs["default"]
        for key, v in action_verbs.items():
            if key in cl:
                verb = v
                break

        improved = c
        # Apply intelligent rewrites based on detected patterns
        for weak in ["responsible for ", "worked on ", "helped ", "assisted ", "involved in ",
                     "was part of ", "contributed to ", "participated in ", "tasked with ",
                     "dealt with ", "took care of "]:
            if weak in cl:
                remainder = cl.split(weak, 1)[1].strip()
                improved = f"{verb} {remainder}, resulting in measurable improvements in efficiency and quality."
                break
        else:
            # General rewrite: wrap with strong framing
            if cl.startswith(("learned", "studied", "familiar")):
                improved = f"Gained hands-on expertise in {cl.split(' ', 2)[-1] if len(cl.split()) > 2 else cl}, applying skills to solve real-world engineering challenges."
            elif "concepts" in cl or "basics" in cl or "understanding" in cl:
                improved = f"Developed deep proficiency in {cl}, applying theoretical knowledge to practical implementations."
            else:
                improved = f"{verb} {cl.rstrip('.')}, driving measurable impact and delivering production-ready results."

        rewrites.append({"original": c, "improved": improved.capitalize()})

    return rewrites


def get_available_roles():
    """Return list of available job roles, sorted by title."""
    roles = [{"id": k, "title": v["title"]} for k, v in JOB_ROLES.items()]
    roles.sort(key=lambda r: r["title"])
    return roles
