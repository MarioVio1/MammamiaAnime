import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeSaturnScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeSaturn"
        self.base_url = "https://www.animesaturn.cx"
        self.enabled = getattr(config, 'AS', '0') == "1"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            # URL di ricerca corretto per AnimeSaturn 2025
            search_url = f"{self.base_url}/animelist"
            params = {'search': query}
            
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # SELETTORI AGGIORNATI PER ANIMESATURN 2025
            # Prova tutti i possibili selettori
            selectors_to_try = [
                'div.item-archivio',           # Selettore principale
                'div.anime-item',              # Alternativo
                'div.card',                    # Card layout
                '.anime-card',                 # Card anime
                'a[href*="/anime/"]',          # Fallback: tutti i link anime
                'div[class*="anime"]',         # Qualsiasi div con "anime"
                'li[class*="item"]',           # Lista item
                'div[class*="item"]'           # Div item
            ]
            
            anime_items = []
            for selector in selectors_to_try:
                try:
                    items = soup.select(selector)
                    if items:
                        print(f"✅ AnimeSaturn: Found {len(items)} items with selector: {selector}")
                        anime_items = items
                        break
                except Exception as e:
                    print(f"❌ Selector {selector} failed: {e}")
                    continue
            
            if not anime_items:
                print("❌ No items found with any selector, trying fallback...")
                # FALLBACK ESTREMO: cerca tutti i link che contengono "anime"
                all_links = soup.find_all('a')
                anime_items = [link for link in all_links if '/anime/' in link.get('href', '')]
                print(f"🔄 Fallback found {len(anime_items)} anime links")
            
            for item in anime_items[:15]:  # Limita a 15 per performance
                try:
                    # Gestione flessibile per diversi tipi di elementi
                    if item.name == 'a':
                        link_elem = item
                        title = item.get('title', '').strip() or item.text.strip()
                    else:
                        link_elem = item.find('a')
                        if not link_elem:
                            continue
                        
                        # Cerca titolo con vari metodi
                        title = ''
                        title_selectors = ['h3', 'h2', 'h4', '.title', '.anime-title', 'span', 'div']
                        for sel in title_selectors:
                            title_elem = item.find(sel)
                            if title_elem and title_elem.text.strip():
                                title = title_elem.text.strip()
                                break
                        
                        if not title:
                            title = link_elem.get('title', '').strip() or link_elem.text.strip()
                    
                    if not title or not link_elem:
                        continue
                    
                    href = link_elem.get('href', '')
                    if not href:
                        continue
                        
                    url = urljoin(self.base_url, href)
                    
                    # Cerca immagine
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    # Filtra solo link anime validi
                    if title and url and '/anime/' in url and len(title) > 2:
                        print(f"   Found: {title} - {url}")
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception as e:
                    print(f"Error parsing item: {e}")
                    continue
            
            print(f"🎯 AnimeSaturn final results: {len(results)}")
            return results
            
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Selettori per episodi AnimeSaturn
            episode_selectors = [
                'a[href*="/ep/"]',
                'a[href*="episodio"]',
                '.episode-link',
                '.ep-link',
                'a[class*="episode"]'
            ]
            
            episode_links = []
            for selector in episode_selectors:
                links = soup.select(selector)
                if links:
                    episode_links = links
                    break
            
            for link in episode_links:
                try:
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_title = link.text.strip()
                    
                    # Estrai numero episodio
                    episode_match = re.search(r'(?:episodio[- ]?|ep[- ]?)(\d+)', episode_title.lower())
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    else:
                        episode_num = len(episodes) + 1
                    
                    episodes.append({
                        'number': episode_num,
                        'title': episode_title or f"Episodio {episode_num}",
                        'url': episode_url
                    })
                    
                except Exception:
                    continue
            
            return sorted(episodes, key=lambda x: x['number'])
            
        except Exception as e:
            print(f"AnimeSaturn episodes error: {e}")
            return []
            
def get_stream_links(self, episode_url):
    if not self.enabled:
        return []
        
    try:
        print(f"🔗 Getting streams from: {episode_url}")
        response = self.make_request(episode_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        streams = []
        
        # Cerca iframe video (FILTRA PUBBLICITÀ)
        iframes = soup.find_all('iframe')
        print(f"📺 Found {len(iframes)} iframes")
        
        for iframe in iframes:
            src = iframe.get('src')
            if src:
                print(f"   Iframe src: {src}")
                
                # ❌ FILTRA PUBBLICITÀ
                if any(ad_domain in src.lower() for ad_domain in ['a-ads.com', 'ads.', 'adnxs.', 'doubleclick.', 'googlesyndication.']):
                    print(f"   ❌ Skipping ad: {src}")
                    continue
                
                # ✅ ACCETTA SOLO SERVER VIDEO VALIDI
                if any(host in src.lower() for host in ['vixcloud', 'streamingaw', 'animeworld', 'streamtape', 'mixdrop', 'doodstream', 'fembed', 'streamhub']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    print(f"   ✅ Valid stream: {src}")
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
        
        # METODO 2: Cerca bottoni di download/streaming
        download_buttons = soup.find_all('a', class_=re.compile(r'btn|button|download|stream'))
        for button in download_buttons:
            href = button.get('href')
            if href and any(ext in href.lower() for ext in ['.mp4', '.m3u8', '.mkv']):
                print(f"   ✅ Download link: {href}")
                streams.append({
                    'url': href,
                    'quality': 'HD',
                    'type': 'direct'
                })
        
        # METODO 3: Cerca nei script JavaScript
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Pattern per trovare URL video reali
                video_patterns = [
                    r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                    r'https?://[^\s"\']+\.(?:mp4|m3u8|mkv)',
                    r'["\']([^"\']*(?:vixcloud|streamingaw|animeworld)[^"\']*)["\']'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        if url and url.startswith('http') and 'ads' not in url.lower():
                            print(f"   ✅ Script video: {url}")
                            streams.append({
                                'url': url,
                                'quality': 'HD',
                                'type': 'direct'
                            })
        
        print(f"🎯 Total valid streams found: {len(streams)}")
        return streams[:5]
        
    except Exception as e:
        print(f"❌ AnimeSaturn stream error: {e}")
        return []


