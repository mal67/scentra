# 🌸 Fragrance Encyclopedia Agent

A free, self-hostable fragrance search engine with fuzzy matching for 192,000+ fragrances.

## ✨ Features

- **Fuzzy Search**: Handles typos, misspellings, and missing special characters
  - "creed aventus" ✓
  - "cred avnetus" ✓ (typos work!)
  - "dior homme" = "Dior Hömme" ✓
  
- **Auto-scraping**: Fetches fragrance notes, ratings, and descriptions from Parfumo
- **Caching**: Scraped data is cached in SQLite (fast repeat queries)
- **Optional AI Summaries**: Uses Groq's free Llama 3.3 70B for natural language descriptions
- **100% Free**: All components have free tiers

## 🚀 Quick Start (Local)

### 1. Clone and Install

```bash
git clone https://github.com/yourusername/fragrance-agent.git
cd fragrance-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Add Your Data

Place your CSV file as `fragrances.csv` in the project root:

```csv
Brand,Name,URL
Creed,Aventus,https://www.parfumo.com/Perfumes/Creed/Aventus
Dior,Sauvage,https://www.parfumo.com/Perfumes/Dior/Sauvage
...
```

### 3. (Optional) Add Groq API Key

Get a free API key from [https://console.groq.com/](https://console.groq.com/)

```bash
# Create secrets file
mkdir -p .streamlit
echo 'GROQ_API_KEY = "your-key-here"' > .streamlit/secrets.toml
```

### 4. Run

```bash
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser!

---

## 🌐 Free Deployment Options

### Option 1: Streamlit Cloud (Recommended) ⭐

**Best for**: Easy setup, custom domain support

1. Push your code to GitHub (make sure `fragrances.csv` is included)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. Add secrets in the Streamlit Cloud dashboard:
   - Go to App Settings → Secrets
   - Add: `GROQ_API_KEY = "your-key"`
5. Deploy!

**Limits**: 1GB RAM, sleeps after inactivity (wakes on request)

---

### Option 2: Hugging Face Spaces

**Best for**: ML community visibility, larger files

1. Create account at [huggingface.co](https://huggingface.co)
2. Create new Space → Select "Streamlit"
3. Upload your files
4. Add secrets in Space settings

**Limits**: 2 vCPU, 16GB RAM (free tier)

---

### Option 3: Railway

**Best for**: More resources, background processing

1. Create account at [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Railway auto-detects Streamlit
4. Add environment variable: `GROQ_API_KEY`

**Limits**: $5/month free credits

---

### Option 4: Render

**Best for**: Simple Docker deployment

1. Create account at [render.com](https://render.com)
2. New → Web Service → Connect repo
3. Set start command: `streamlit run app.py --server.port $PORT`
4. Add env vars

**Limits**: 512MB RAM, spins down after 15 min inactivity

---

## 📁 Project Structure

```
fragrance-agent/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── fragrances.csv        # Your fragrance dataset
├── fragrance_cache.db    # Auto-created SQLite cache
├── .streamlit/
│   └── secrets.toml      # API keys (don't commit!)
└── README.md
```

---

## 🔧 How It Works

### 1. Fuzzy Matching
Uses `rapidfuzz` library with weighted ratio scoring:

```python
from rapidfuzz import fuzz, process

# Handles:
# - Typos: "avnetus" → "Aventus"  
# - Missing accents: "Moiré" → "Moire"
# - Partial matches: "aventus" → "Creed Aventus"
```

### 2. Text Normalization
Before matching, text is normalized:

```python
def normalize_text(text):
    text = text.lower()
    text = remove_accents(text)  # é → e
    text = remove_special_chars(text)  # remove punctuation
    return text
```

### 3. Web Scraping + Caching
- First request: Scrapes Parfumo, stores in SQLite
- Subsequent requests: Instant from cache
- Cache persists between sessions

### 4. LLM Integration (Optional)
If Groq API key is provided:
- Generates natural language summaries
- Uses Llama 3.3 70B (free, fast)
- Falls back to basic formatting if no key

---

## 📊 CSV Format

Your CSV should have 3 columns (no header required):

| Column | Description | Example |
|--------|-------------|---------|
| Brand | Fragrance house | `Creed` |
| Name | Fragrance name | `Aventus` |
| URL | Parfumo link | `https://www.parfumo.com/Perfumes/Creed/Aventus` |

---

## 🛠️ Customization

### Change Match Threshold

In `app.py`, adjust the score threshold:

```python
if score > 50:  # Increase for stricter matching
```

### Add More Data Sources

Extend `scrape_parfumo()` to handle other sites:

```python
def scrape_fragrantica(url, cache_conn):
    # Similar structure, different selectors
    ...
```

### Use Different LLMs

Replace Groq with any OpenAI-compatible API:

```python
# Use Together.ai, OpenRouter, etc.
client = OpenAI(
    base_url="https://api.together.xyz/v1",
    api_key=os.getenv("TOGETHER_API_KEY")
)
```

---

## 🆓 Free LLM Options

| Provider | Model | Free Tier | Speed |
|----------|-------|-----------|-------|
| **Groq** | Llama 3.3 70B | 30 req/min | ⚡ Fastest |
| Together.ai | Llama 3.1 | $25 credits | Fast |
| OpenRouter | Various | Pay-per-use | Varies |
| Google | Gemini 1.5 | 60 req/min | Fast |
| Local | Ollama | Unlimited | Depends on HW |

---

## 🐛 Troubleshooting

**"No fragrances found"**
- Check your CSV file exists and has correct format
- Try a broader search term

**Scraping errors**
- Parfumo may rate-limit heavy usage
- Cached data still works
- Check your internet connection

**Slow first search**
- Initial CSV loading takes ~5-10 seconds for 192K rows
- Subsequent searches are instant (cached)

---

## 📜 License

MIT License - Use freely!

---

## 🤝 Contributing

PRs welcome! Ideas for improvements:
- [ ] Image scraping for fragrance bottles
- [ ] Price comparison from retailers
- [ ] User favorites/collections
- [ ] Scent similarity recommendations
