import streamlit as st
import pandas as pd
from rapidfuzz import fuzz, process
import requests
from bs4 import BeautifulSoup
import sqlite3
import json
import re
from pathlib import Path
import unicodedata
from groq import Groq
import os

# Page config
st.set_page_config(
    page_title="Fragrance Encyclopedia",
    page_icon="🌸",
    layout="wide"
)

# Initialize session state
if 'cache_db' not in st.session_state:
    st.session_state.cache_db = None

# --- Database Setup for Caching ---
def init_cache_db():
    """Initialize SQLite cache for scraped fragrance data"""
    conn = sqlite3.connect('fragrance_cache.db', check_same_thread=False)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS fragrance_cache (
            url TEXT PRIMARY KEY,
            data TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

# --- Text Normalization for Fuzzy Matching ---
def normalize_text(text):
    """Normalize text for better fuzzy matching"""
    if not isinstance(text, str):
        return ""
    # Convert to lowercase
    text = text.lower()
    # Remove accents/diacritics
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Remove special characters but keep spaces
    text = re.sub(r'[^a-z0-9\s]', '', text)
    # Normalize whitespace
    text = ' '.join(text.split())
    return text

# --- Load Fragrance Data ---
@st.cache_data
def load_fragrance_data():
    """Load and preprocess fragrance dataset"""
    try:
        # Try to load from CSV
        df = pd.read_csv('fragrances.csv', header=None, names=['brand', 'name', 'url'])
    except FileNotFoundError:
        st.error("⚠️ Please upload your fragrances.csv file to the app directory")
        return None
    
    # Create combined search field
    df['full_name'] = df['brand'] + ' ' + df['name']
    # Create normalized version for fuzzy matching
    df['normalized'] = df['full_name'].apply(normalize_text)
    
    return df

# --- Fuzzy Search ---
def search_fragrance(query, df, limit=5):
    """Search for fragrances using fuzzy matching"""
    normalized_query = normalize_text(query)
    
    # Get all normalized names as a list
    choices = df['normalized'].tolist()
    
    # Use RapidFuzz to find best matches
    results = process.extract(
        normalized_query, 
        choices, 
        scorer=fuzz.WRatio,  # Weighted ratio handles partial matches well
        limit=limit
    )
    
    # Get matching rows
    matches = []
    for match_text, score, idx in results:
        if score > 50:  # Minimum threshold
            row = df.iloc[idx]
            matches.append({
                'brand': row['brand'],
                'name': row['name'],
                'full_name': row['full_name'],
                'url': row['url'],
                'score': score
            })
    
    return matches

# --- Web Scraping ---
def scrape_parfumo(url, cache_conn):
    """Scrape fragrance details from Parfumo with caching"""
    
    # Check cache first
    cursor = cache_conn.execute(
        "SELECT data FROM fragrance_cache WHERE url = ?", (url,)
    )
    cached = cursor.fetchone()
    if cached:
        return json.loads(cached[0])
    
    # Scrape the page
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        data = {
            'url': url,
            'notes': extract_notes(soup),
            'rating': extract_rating(soup),
            'description': extract_description(soup),
            'accords': extract_accords(soup),
            'longevity': extract_longevity(soup),
            'sillage': extract_sillage(soup)
        }
        
        # Cache the result
        cache_conn.execute(
            "INSERT OR REPLACE INTO fragrance_cache (url, data) VALUES (?, ?)",
            (url, json.dumps(data))
        )
        cache_conn.commit()
        
        return data
        
    except Exception as e:
        return {'error': str(e), 'url': url}

def extract_notes(soup):
    """Extract fragrance notes from Parfumo page"""
    notes = {'top': [], 'heart': [], 'base': []}
    
    # Try to find note pyramids
    note_sections = soup.find_all('div', class_='pyramid-level')
    
    for section in note_sections:
        level_name = section.get('class', [])
        level_text = section.get_text(strip=True).lower()
        
        note_items = section.find_all('span', class_='note-name')
        note_list = [n.get_text(strip=True) for n in note_items]
        
        if 'top' in level_text or 'head' in level_text:
            notes['top'] = note_list
        elif 'heart' in level_text or 'middle' in level_text:
            notes['heart'] = note_list
        elif 'base' in level_text or 'bottom' in level_text:
            notes['base'] = note_list
    
    # Alternative extraction method if pyramid not found
    if not any(notes.values()):
        # Look for notes in general note containers
        note_containers = soup.find_all(['div', 'span'], class_=re.compile(r'note|ingredient', re.I))
        all_notes = []
        for container in note_containers:
            text = container.get_text(strip=True)
            if text and len(text) < 50:  # Likely a single note
                all_notes.append(text)
        if all_notes:
            notes['all'] = list(set(all_notes))[:20]  # Dedupe and limit
    
    return notes

def extract_rating(soup):
    """Extract rating from Parfumo page"""
    try:
        # Look for rating elements
        rating_elem = soup.find(['span', 'div'], class_=re.compile(r'rating|score', re.I))
        if rating_elem:
            text = rating_elem.get_text(strip=True)
            # Extract numeric rating
            match = re.search(r'(\d+\.?\d*)', text)
            if match:
                return float(match.group(1))
    except:
        pass
    return None

def extract_description(soup):
    """Extract fragrance description"""
    try:
        desc_elem = soup.find(['div', 'p'], class_=re.compile(r'description|about', re.I))
        if desc_elem:
            return desc_elem.get_text(strip=True)[:500]  # Limit length
    except:
        pass
    return None

def extract_accords(soup):
    """Extract fragrance accords (scent categories)"""
    accords = []
    try:
        accord_elems = soup.find_all(['span', 'div'], class_=re.compile(r'accord', re.I))
        for elem in accord_elems:
            text = elem.get_text(strip=True)
            if text and len(text) < 30:
                accords.append(text)
    except:
        pass
    return list(set(accords))[:10]

def extract_longevity(soup):
    """Extract longevity rating"""
    try:
        elem = soup.find(string=re.compile(r'longevity', re.I))
        if elem:
            parent = elem.find_parent()
            if parent:
                match = re.search(r'(\d+\.?\d*)', parent.get_text())
                if match:
                    return float(match.group(1))
    except:
        pass
    return None

def extract_sillage(soup):
    """Extract sillage (projection) rating"""
    try:
        elem = soup.find(string=re.compile(r'sillage', re.I))
        if elem:
            parent = elem.find_parent()
            if parent:
                match = re.search(r'(\d+\.?\d*)', parent.get_text())
                if match:
                    return float(match.group(1))
    except:
        pass
    return None

# --- LLM Response Generation (Optional) ---
def generate_llm_response(fragrance_name, fragrance_data):
    """Use Groq's free LLM to generate a nice response"""
    
    groq_key = os.getenv('GROQ_API_KEY') or st.secrets.get('GROQ_API_KEY', '')
    
    if not groq_key:
        # Return formatted response without LLM
        return format_basic_response(fragrance_name, fragrance_data)
    
    try:
        client = Groq(api_key=groq_key)
        
        prompt = f"""You are a fragrance expert. Based on the following data about "{fragrance_name}", 
        provide a brief, engaging description in 2-3 sentences. Be concise and informative.
        
        Data: {json.dumps(fragrance_data, indent=2)}
        
        Focus on the key notes and what kind of scent experience to expect."""
        
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=200
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return format_basic_response(fragrance_name, fragrance_data)

def format_basic_response(name, data):
    """Format response without LLM"""
    parts = [f"**{name}**\n"]
    
    if data.get('notes'):
        notes = data['notes']
        if notes.get('top'):
            parts.append(f"🔝 **Top notes:** {', '.join(notes['top'])}")
        if notes.get('heart'):
            parts.append(f"❤️ **Heart notes:** {', '.join(notes['heart'])}")
        if notes.get('base'):
            parts.append(f"🌳 **Base notes:** {', '.join(notes['base'])}")
        if notes.get('all'):
            parts.append(f"🎵 **Notes:** {', '.join(notes['all'])}")
    
    if data.get('rating'):
        parts.append(f"⭐ **Rating:** {data['rating']}/10")
    
    if data.get('accords'):
        parts.append(f"🎨 **Accords:** {', '.join(data['accords'])}")
    
    if data.get('description'):
        parts.append(f"\n📝 {data['description']}")
    
    return '\n'.join(parts)

# --- Main App ---
def main():
    st.title("🌸 Fragrance Encyclopedia")
    st.markdown("*Search 192,000+ fragrances - handles typos and special characters!*")
    
    # Load data
    df = load_fragrance_data()
    if df is None:
        return
    
    # Initialize cache
    cache_conn = init_cache_db()
    
    # Search input
    query = st.text_input(
        "🔍 Search for a fragrance",
        placeholder="e.g., 'creed aventus', 'chanel no 5', 'dior sauvage'...",
        help="Don't worry about spelling or special characters!"
    )
    
    if query:
        with st.spinner("Searching..."):
            matches = search_fragrance(query, df)
        
        if not matches:
            st.warning("No fragrances found. Try a different search term.")
            return
        
        # Show matches
        st.subheader(f"Found {len(matches)} match(es)")
        
        # Let user select which one
        for i, match in enumerate(matches):
            col1, col2 = st.columns([4, 1])
            
            with col1:
                st.markdown(f"**{match['full_name']}**")
                st.caption(f"Match confidence: {match['score']}%")
            
            with col2:
                if st.button("View Details", key=f"btn_{i}"):
                    st.session_state.selected_fragrance = match
        
        # Show details if selected
        if 'selected_fragrance' in st.session_state:
            match = st.session_state.selected_fragrance
            st.divider()
            
            with st.spinner(f"Fetching details for {match['full_name']}..."):
                data = scrape_parfumo(match['url'], cache_conn)
            
            if 'error' in data:
                st.error(f"Could not fetch details: {data['error']}")
                st.markdown(f"[View on Parfumo]({match['url']})")
            else:
                # Display fragrance info
                st.subheader(f"🌺 {match['full_name']}")
                
                # Notes pyramid
                if data.get('notes'):
                    notes = data['notes']
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if notes.get('top'):
                            st.markdown("**🔝 Top Notes**")
                            for note in notes['top']:
                                st.markdown(f"• {note}")
                    
                    with col2:
                        if notes.get('heart'):
                            st.markdown("**❤️ Heart Notes**")
                            for note in notes['heart']:
                                st.markdown(f"• {note}")
                    
                    with col3:
                        if notes.get('base'):
                            st.markdown("**🌳 Base Notes**")
                            for note in notes['base']:
                                st.markdown(f"• {note}")
                    
                    if notes.get('all') and not any([notes.get('top'), notes.get('heart'), notes.get('base')]):
                        st.markdown("**🎵 Notes**")
                        st.markdown(", ".join(notes['all']))
                
                # Rating and other info
                info_col1, info_col2 = st.columns(2)
                
                with info_col1:
                    if data.get('rating'):
                        st.metric("⭐ Rating", f"{data['rating']}/10")
                    if data.get('longevity'):
                        st.metric("⏱️ Longevity", f"{data['longevity']}/10")
                
                with info_col2:
                    if data.get('sillage'):
                        st.metric("💨 Sillage", f"{data['sillage']}/10")
                    if data.get('accords'):
                        st.markdown("**🎨 Accords**")
                        st.markdown(", ".join(data['accords']))
                
                # Description
                if data.get('description'):
                    st.markdown("**📝 Description**")
                    st.markdown(data['description'])
                
                # LLM Summary (if Groq key available)
                if os.getenv('GROQ_API_KEY') or st.secrets.get('GROQ_API_KEY'):
                    with st.expander("🤖 AI Summary"):
                        with st.spinner("Generating summary..."):
                            summary = generate_llm_response(match['full_name'], data)
                            st.markdown(summary)
                
                # Link to source
                st.markdown(f"[🔗 View on Parfumo]({match['url']})")
    
    # Footer
    st.divider()
    st.caption(f"📊 Database contains {len(df):,} fragrances")

if __name__ == "__main__":
    main()
