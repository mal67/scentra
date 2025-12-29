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
import os
import base64

# Page config
st.set_page_config(
    page_title="Fragrance Encyclopedia",
    page_icon="🌸",
    layout="wide"
)

# --- Dynamic Bottle SVG Generator with 3D Rotation ---
def render_3d_bottle(brand, name, bottle_id="bottle"):
    """Render a realistic 3D perfume bottle using Three.js"""
    brand_display = brand.upper()[:18]
    name_display = name.upper()[:22]
    
    html = f'''
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            * {{ margin: 0; padding: 0; }}
            body {{ 
                background: transparent;
                overflow: hidden;
            }}
            #container-{bottle_id} {{
                width: 250px;
                height: 320px;
                cursor: grab;
            }}
            #container-{bottle_id}:active {{
                cursor: grabbing;
            }}
            .hint {{
                text-align: center;
                font-size: 11px;
                color: #888;
                font-family: -apple-system, BlinkMacSystemFont, sans-serif;
                margin-top: -5px;
            }}
        </style>
    </head>
    <body>
        <div id="container-{bottle_id}"></div>
        <div class="hint">🖱️ Drag to rotate</div>
        
        <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
        <script>
        (function() {{
            const container = document.getElementById('container-{bottle_id}');
            const width = 250;
            const height = 320;
            
            // Scene setup
            const scene = new THREE.Scene();
            scene.background = null;
            
            // Camera
            const camera = new THREE.PerspectiveCamera(35, width / height, 0.1, 1000);
            camera.position.set(0, 0, 6);
            
            // Renderer
            const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
            renderer.setSize(width, height);
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.shadowMap.enabled = true;
            renderer.shadowMap.type = THREE.PCFSoftShadowMap;
            container.appendChild(renderer.domElement);
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
            scene.add(ambientLight);
            
            const mainLight = new THREE.DirectionalLight(0xffffff, 0.8);
            mainLight.position.set(5, 10, 7);
            mainLight.castShadow = true;
            scene.add(mainLight);
            
            const fillLight = new THREE.DirectionalLight(0xffffff, 0.3);
            fillLight.position.set(-5, 5, -5);
            scene.add(fillLight);
            
            const rimLight = new THREE.DirectionalLight(0xaaccff, 0.4);
            rimLight.position.set(0, 0, -10);
            scene.add(rimLight);
            
            // Bottle group
            const bottleGroup = new THREE.Group();
            
            // Glass material
            const glassMaterial = new THREE.MeshPhysicalMaterial({{
                color: 0xffffff,
                metalness: 0.0,
                roughness: 0.05,
                transmission: 0.95,
                thickness: 0.5,
                envMapIntensity: 1,
                clearcoat: 1,
                clearcoatRoughness: 0.1,
                transparent: true,
                opacity: 0.9
            }});
            
            // Bottle body - rounded box shape
            const bodyWidth = 1.4;
            const bodyHeight = 2.0;
            const bodyDepth = 0.7;
            const bodyGeometry = new THREE.BoxGeometry(bodyWidth, bodyHeight, bodyDepth, 8, 8, 8);
            
            // Round the edges
            const positions = bodyGeometry.attributes.position;
            const radius = 0.12;
            for (let i = 0; i < positions.count; i++) {{
                let x = positions.getX(i);
                let y = positions.getY(i);
                let z = positions.getZ(i);
                
                // Smooth corners
                const fx = Math.abs(x) > bodyWidth/2 - radius ? Math.sign(x) * (bodyWidth/2 - radius + radius * Math.cos(Math.asin(Math.min(1, Math.abs(x)/(bodyWidth/2))))) : x;
                const fz = Math.abs(z) > bodyDepth/2 - radius ? Math.sign(z) * (bodyDepth/2 - radius + radius * Math.cos(Math.asin(Math.min(1, Math.abs(z)/(bodyDepth/2))))) : z;
            }}
            bodyGeometry.computeVertexNormals();
            
            const bottleBody = new THREE.Mesh(bodyGeometry, glassMaterial);
            bottleBody.position.y = -0.3;
            bottleBody.castShadow = true;
            bottleBody.receiveShadow = true;
            bottleGroup.add(bottleBody);
            
            // Bottle neck
            const neckGeometry = new THREE.CylinderGeometry(0.18, 0.22, 0.4, 16);
            const neck = new THREE.Mesh(neckGeometry, glassMaterial);
            neck.position.y = 0.9;
            bottleGroup.add(neck);
            
            // Spray nozzle
            const nozzleGeometry = new THREE.CylinderGeometry(0.08, 0.12, 0.15, 12);
            const nozzleMaterial = new THREE.MeshStandardMaterial({{
                color: 0xc0c0c0,
                metalness: 0.9,
                roughness: 0.2
            }});
            const nozzle = new THREE.Mesh(nozzleGeometry, nozzleMaterial);
            nozzle.position.y = 1.15;
            bottleGroup.add(nozzle);
            
            // Cap material
            const capMaterial = new THREE.MeshStandardMaterial({{
                color: 0x1a1a1a,
                metalness: 0.3,
                roughness: 0.4
            }});
            
            // Cap body
            const capGeometry = new THREE.BoxGeometry(0.55, 0.7, 0.55, 4, 4, 4);
            const cap = new THREE.Mesh(capGeometry, capMaterial);
            cap.position.y = 1.55;
            bottleGroup.add(cap);
            
            // Cap top (slightly beveled)
            const capTopGeometry = new THREE.BoxGeometry(0.5, 0.08, 0.5);
            const capTopMaterial = new THREE.MeshStandardMaterial({{
                color: 0x2a2a2a,
                metalness: 0.4,
                roughness: 0.3
            }});
            const capTop = new THREE.Mesh(capTopGeometry, capTopMaterial);
            capTop.position.y = 1.94;
            bottleGroup.add(capTop);
            
            // Label on bottle
            const canvas = document.createElement('canvas');
            canvas.width = 512;
            canvas.height = 256;
            const ctx = canvas.getContext('2d');
            
            // Label background (subtle)
            ctx.fillStyle = 'rgba(255, 255, 255, 0.1)';
            ctx.fillRect(0, 0, 512, 256);
            
            // Brand name
            ctx.fillStyle = '#1a1a1a';
            ctx.font = 'bold 52px Georgia, serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText('{brand_display}', 256, 95);
            
            // Decorative line
            ctx.strokeStyle = '#888888';
            ctx.lineWidth = 2;
            ctx.beginPath();
            ctx.moveTo(80, 130);
            ctx.lineTo(432, 130);
            ctx.stroke();
            
            // Fragrance name
            ctx.fillStyle = '#333333';
            ctx.font = '36px Georgia, serif';
            ctx.fillText('{name_display}', 256, 175);
            
            const labelTexture = new THREE.CanvasTexture(canvas);
            labelTexture.anisotropy = renderer.capabilities.getMaxAnisotropy();
            
            const labelMaterial = new THREE.MeshBasicMaterial({{
                map: labelTexture,
                transparent: true,
                opacity: 0.95
            }});
            
            const labelGeometry = new THREE.PlaneGeometry(1.2, 0.6);
            const label = new THREE.Mesh(labelGeometry, labelMaterial);
            label.position.set(0, -0.3, bodyDepth/2 + 0.01);
            bottleGroup.add(label);
            
            // Back label (mirror)
            const labelBack = new THREE.Mesh(labelGeometry, labelMaterial);
            labelBack.position.set(0, -0.3, -bodyDepth/2 - 0.01);
            labelBack.rotation.y = Math.PI;
            bottleGroup.add(labelBack);
            
            // Add liquid inside
            const liquidGeometry = new THREE.BoxGeometry(bodyWidth - 0.15, bodyHeight - 0.3, bodyDepth - 0.15);
            const liquidMaterial = new THREE.MeshPhysicalMaterial({{
                color: 0xfff8dc,
                metalness: 0,
                roughness: 0.1,
                transmission: 0.6,
                thickness: 1,
                transparent: true,
                opacity: 0.4
            }});
            const liquid = new THREE.Mesh(liquidGeometry, liquidMaterial);
            liquid.position.y = -0.4;
            bottleGroup.add(liquid);
            
            // Bottom accent
            const bottomGeometry = new THREE.BoxGeometry(bodyWidth + 0.02, 0.08, bodyDepth + 0.02);
            const bottomMaterial = new THREE.MeshStandardMaterial({{
                color: 0x2a2a2a,
                metalness: 0.5,
                roughness: 0.3
            }});
            const bottom = new THREE.Mesh(bottomGeometry, bottomMaterial);
            bottom.position.y = -1.34;
            bottleGroup.add(bottom);
            
            scene.add(bottleGroup);
            
            // Shadow plane
            const shadowGeometry = new THREE.PlaneGeometry(5, 5);
            const shadowMaterial = new THREE.ShadowMaterial({{ opacity: 0.15 }});
            const shadowPlane = new THREE.Mesh(shadowGeometry, shadowMaterial);
            shadowPlane.rotation.x = -Math.PI / 2;
            shadowPlane.position.y = -1.5;
            shadowPlane.receiveShadow = true;
            scene.add(shadowPlane);
            
            // Mouse interaction
            let isDragging = false;
            let previousMousePosition = {{ x: 0, y: 0 }};
            let targetRotationY = 0;
            let targetRotationX = 0;
            let currentRotationY = 0;
            let currentRotationX = 0;
            
            container.addEventListener('mousedown', (e) => {{
                isDragging = true;
                previousMousePosition = {{ x: e.clientX, y: e.clientY }};
            }});
            
            document.addEventListener('mousemove', (e) => {{
                if (!isDragging) return;
                
                const deltaX = e.clientX - previousMousePosition.x;
                const deltaY = e.clientY - previousMousePosition.y;
                
                targetRotationY += deltaX * 0.01;
                targetRotationX += deltaY * 0.01;
                targetRotationX = Math.max(-0.5, Math.min(0.5, targetRotationX));
                
                previousMousePosition = {{ x: e.clientX, y: e.clientY }};
            }});
            
            document.addEventListener('mouseup', () => {{
                isDragging = false;
            }});
            
            // Touch support
            container.addEventListener('touchstart', (e) => {{
                isDragging = true;
                previousMousePosition = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
            }});
            
            container.addEventListener('touchmove', (e) => {{
                if (!isDragging) return;
                e.preventDefault();
                
                const deltaX = e.touches[0].clientX - previousMousePosition.x;
                const deltaY = e.touches[0].clientY - previousMousePosition.y;
                
                targetRotationY += deltaX * 0.01;
                targetRotationX += deltaY * 0.01;
                targetRotationX = Math.max(-0.5, Math.min(0.5, targetRotationX));
                
                previousMousePosition = {{ x: e.touches[0].clientX, y: e.touches[0].clientY }};
            }});
            
            container.addEventListener('touchend', () => {{
                isDragging = false;
            }});
            
            // Auto rotation when not dragging
            let autoRotate = true;
            let lastInteraction = 0;
            
            // Animation loop
            function animate() {{
                requestAnimationFrame(animate);
                
                // Smooth rotation interpolation
                currentRotationY += (targetRotationY - currentRotationY) * 0.1;
                currentRotationX += (targetRotationX - currentRotationX) * 0.1;
                
                // Auto rotate when idle
                if (!isDragging && Date.now() - lastInteraction > 2000) {{
                    targetRotationY += 0.003;
                }}
                
                if (isDragging) {{
                    lastInteraction = Date.now();
                }}
                
                bottleGroup.rotation.y = currentRotationY;
                bottleGroup.rotation.x = currentRotationX;
                
                renderer.render(scene, camera);
            }}
            
            animate();
        }})();
        </script>
    </body>
    </html>
    '''
    return html


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
    text = text.lower()
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r'[^a-z0-9\s]', '', text)
    text = ' '.join(text.split())
    return text


# --- Load Fragrance Data ---
@st.cache_data
def load_fragrance_data():
    """Load and preprocess fragrance dataset"""
    try:
        df = pd.read_csv('fragrances.csv', header=None, names=['brand', 'name', 'url'])
    except FileNotFoundError:
        st.error("⚠️ Please upload your fragrances.csv file to the app directory")
        return None
    
    df['full_name'] = df['brand'] + ' ' + df['name']
    df['normalized'] = df['full_name'].apply(normalize_text)
    return df


# --- Fuzzy Search ---
def search_fragrance(query, df, limit=5):
    """Search for fragrances using fuzzy matching"""
    normalized_query = normalize_text(query)
    choices = df['normalized'].tolist()
    
    results = process.extract(
        normalized_query, 
        choices, 
        scorer=fuzz.WRatio,
        limit=limit
    )
    
    matches = []
    for match_text, score, idx in results:
        if score > 50:
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
    
    cursor = cache_conn.execute(
        "SELECT data FROM fragrance_cache WHERE url = ?", (url,)
    )
    cached = cursor.fetchone()
    if cached:
        return json.loads(cached[0])
    
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
        
        cache_conn.execute(
            "INSERT OR REPLACE INTO fragrance_cache (url, data) VALUES (?, ?)",
            (url, json.dumps(data))
        )
        cache_conn.commit()
        
        return data
        
    except Exception as e:
        return {'error': str(e), 'url': url}


def extract_notes(soup):
    """Extract fragrance notes from Parfumo page - properly parsing the pyramid structure"""
    notes = {'top': [], 'heart': [], 'base': []}
    
    try:
        html_str = str(soup)
        
        top_pos = html_str.find('pyr_top')
        middle_pos = html_str.find('pyr_middle')
        base_pos = html_str.find('pyr_base')
        
        if top_pos > 0 and middle_pos > 0 and base_pos > 0:
            top_section = html_str[top_pos:middle_pos]
            heart_section = html_str[middle_pos:base_pos]
            base_section = html_str[base_pos:base_pos + 2000]
            
            alt_pattern = r'alt="([^"]+)"'
            
            top_alts = re.findall(alt_pattern, top_section)
            for alt in top_alts:
                if alt and len(alt) < 40 and 'Top' not in alt and 'Notes' not in alt and 'pyr' not in alt.lower():
                    if alt not in notes['top']:
                        notes['top'].append(alt)
            
            heart_alts = re.findall(alt_pattern, heart_section)
            for alt in heart_alts:
                if alt and len(alt) < 40 and 'Heart' not in alt and 'Middle' not in alt and 'Notes' not in alt and 'pyr' not in alt.lower():
                    if alt not in notes['heart']:
                        notes['heart'].append(alt)
            
            base_alts = re.findall(alt_pattern, base_section)
            for alt in base_alts:
                if alt and len(alt) < 40 and 'Base' not in alt and 'Notes' not in alt and 'pyr' not in alt.lower():
                    if 'Rating' in alt or 'Scent' in alt or 'Review' in alt:
                        break
                    if alt not in notes['base']:
                        notes['base'].append(alt)
    
    except Exception:
        pass
    
    if not any(notes.values()):
        try:
            all_imgs = soup.find_all('img')
            current_level = None
            
            for img in all_imgs:
                src = img.get('src', '')
                alt = img.get('alt', '')
                
                if 'pyr_top' in src:
                    current_level = 'top'
                    continue
                elif 'pyr_middle' in src:
                    current_level = 'heart'
                    continue
                elif 'pyr_base' in src:
                    current_level = 'base'
                    continue
                
                if current_level and 'media.parfumo' in src and '/notes/' in src:
                    if alt and len(alt) < 40:
                        if alt not in notes[current_level]:
                            notes[current_level].append(alt)
        except Exception:
            pass
    
    if not any(notes.values()):
        try:
            all_notes = []
            for img in soup.find_all('img', alt=True):
                src = img.get('src', '')
                alt = img.get('alt', '')
                if 'notes' in src.lower() and alt and len(alt) < 40:
                    if alt not in all_notes:
                        all_notes.append(alt)
            if all_notes:
                notes['all'] = all_notes[:15]
        except Exception:
            pass
    
    return notes


def extract_rating(soup):
    """Extract rating from Parfumo page"""
    try:
        text = soup.get_text()
        match = re.search(r'(\d+\.?\d*)\s*/\s*10\s*\n?\s*\d+\s*Ratings', text)
        if match:
            return float(match.group(1))
        
        match2 = re.search(r'(\d+\.\d)\s*/\s*10', text)
        if match2:
            return float(match2.group(1))
    except:
        pass
    return None


def extract_description(soup):
    """Extract fragrance description from Parfumo page"""
    try:
        text = soup.get_text()
        match = re.search(r'(A\s+(?:popular\s+)?(?:limited\s+)?perfume\s+by\s+[^.]+\.(?:\s+[^.]+\.){0,2})', text)
        if match:
            desc = match.group(1).strip()
            desc = ' '.join(desc.split())
            return desc[:500]
        
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            return meta_desc.get('content', '')[:500]
    except:
        pass
    return None


def extract_accords(soup):
    """Extract fragrance accords from Parfumo"""
    accords = []
    try:
        text = soup.get_text()
        match = re.search(r'Main accords\s*([\s\S]*?)(?:SMELL|Fragrance Pyramid|Ratings|$)', text)
        if match:
            accords_text = match.group(1)
            common_accords = ['Fresh', 'Fruity', 'Citrus', 'Woody', 'Smoky', 'Floral', 
                           'Spicy', 'Sweet', 'Powdery', 'Musky', 'Green', 'Aquatic',
                           'Oriental', 'Balsamic', 'Earthy', 'Leather', 'Amber',
                           'Vanilla', 'Aromatic', 'Ozonic', 'Warm', 'Creamy',
                           'Resinous', 'Animalic', 'Gourmand', 'Tobacco', 'Boozy',
                           'Synthetic', 'Mossy', 'Herbal', 'Soapy', 'Marine']
            
            for accord in common_accords:
                if accord in accords_text:
                    accords.append(accord)
        return accords[:6]
    except:
        pass
    return accords


def extract_longevity(soup):
    """Extract longevity rating from Parfumo page"""
    try:
        text = soup.get_text()
        match = re.search(r'Longevity\s*(\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
    except:
        pass
    return None


def extract_sillage(soup):
    """Extract sillage rating from Parfumo page"""
    try:
        text = soup.get_text()
        match = re.search(r'Sillage\s*(\d+\.?\d*)', text)
        if match:
            return float(match.group(1))
    except:
        pass
    return None


# --- LLM Response Generation (Optional) ---
def generate_llm_response(fragrance_name, fragrance_data):
    """Use Groq's free LLM to generate a nice response"""
    
    groq_key = os.getenv('GROQ_API_KEY')
    
    if not groq_key:
        return None
    
    try:
        from groq import Groq
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
        
    except Exception:
        return None


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
        
        st.subheader(f"Found {len(matches)} match(es)")
        
        top_match = matches[0]
        
        col_bottle, col_info = st.columns([1, 2])
        
        with col_bottle:
            bottle_html = render_3d_bottle(top_match['brand'], top_match['name'], "top")
            st.components.v1.html(bottle_html, height=360)
        
        with col_info:
            st.markdown(f"### 🏆 Top Match")
            st.markdown(f"**{top_match['full_name']}**")
            st.caption(f"Match confidence: {top_match['score']}%")
            if st.button("View Details", key="btn_top"):
                st.session_state.selected_fragrance = top_match
        
        if len(matches) > 1:
            st.markdown("---")
            st.markdown("**Other matches:**")
            for i, match in enumerate(matches[1:], 1):
                col1, col2 = st.columns([4, 1])
                
                with col1:
                    st.markdown(f"**{match['full_name']}**")
                    st.caption(f"Match confidence: {match['score']}%")
                
                with col2:
                    if st.button("View Details", key=f"btn_{i}"):
                        st.session_state.selected_fragrance = match
        
        if 'selected_fragrance' in st.session_state:
            match = st.session_state.selected_fragrance
            st.divider()
            
            with st.spinner(f"Fetching details for {match['full_name']}..."):
                data = scrape_parfumo(match['url'], cache_conn)
            
            if 'error' in data:
                st.error(f"Could not fetch details: {data['error']}")
                st.markdown(f"[View on Parfumo]({match['url']})")
            else:
                detail_col1, detail_col2 = st.columns([1, 2])
                
                with detail_col1:
                    bottle_html = render_3d_bottle(match['brand'], match['name'], "detail")
                    st.components.v1.html(bottle_html, height=360)
                
                with detail_col2:
                    st.subheader(f"🌺 {match['full_name']}")
                    if data.get('rating'):
                        st.metric("⭐ Rating", f"{data['rating']}/10")
                
                if data.get('notes'):
                    st.markdown("### 🎵 Fragrance Pyramid")
                    notes = data['notes']
                    
                    has_pyramid = notes.get('top') or notes.get('heart') or notes.get('base')
                    
                    if has_pyramid:
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            if notes.get('top'):
                                st.markdown("**🔝 TOP NOTES**")
                                st.markdown(", ".join(notes['top']))
                        
                        with col2:
                            if notes.get('heart'):
                                st.markdown("**❤️ HEART NOTES**")
                                st.markdown(", ".join(notes['heart']))
                        
                        with col3:
                            if notes.get('base'):
                                st.markdown("**🌳 BASE NOTES**")
                                st.markdown(", ".join(notes['base']))
                    else:
                        if notes.get('all'):
                            st.markdown("**🎵 Notes**")
                            st.markdown(", ".join(notes['all']))
                
                st.markdown("### 📊 Performance")
                info_col1, info_col2, info_col3 = st.columns(3)
                
                with info_col1:
                    if data.get('rating'):
                        st.metric("⭐ Rating", f"{data['rating']}/10")
                
                with info_col2:
                    if data.get('longevity'):
                        st.metric("⏱️ Longevity", f"{data['longevity']}/10")
                
                with info_col3:
                    if data.get('sillage'):
                        st.metric("💨 Sillage", f"{data['sillage']}/10")
                
                if data.get('accords'):
                    st.markdown("### 🎨 Accords")
                    st.markdown(", ".join(data['accords']))
                
                if data.get('description'):
                    st.markdown("### 📝 Description")
                    st.markdown(data['description'])
                
                # LLM Summary (optional - only if GROQ_API_KEY env var is set)
                groq_key = os.getenv('GROQ_API_KEY')
                if groq_key:
                    with st.expander("🤖 AI Summary"):
                        with st.spinner("Generating summary..."):
                            summary = generate_llm_response(match['full_name'], data)
                            if summary:
                                st.markdown(summary)
                            else:
                                st.info("Could not generate AI summary")
                
                st.markdown(f"[🔗 View on Parfumo]({match['url']})")
    
    st.divider()
    st.caption(f"📊 Database contains {len(df):,} fragrances")


if __name__ == "__main__":
    main()