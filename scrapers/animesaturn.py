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
            print(f"🔍 AnimeSaturn searching for: {query}")
            search_url = f"{self.base_url}/animelist"
            params = {'search': query}
            
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            selectors_to_try = [
                'div.item-archivio',
                'div.anime-item',
                'div.card',
                '.anime-card',
                'a[href*="/anime/"]'
            ]
            
            anime_items = []
            for selector in selectors_to_try:
                try:
                    items = soup.select(selector)
                    if items:
                        print(f"✅ Found {len(items)} items with: {selector}")
                        anime_items = items
                        break
                except Exception:
                    continue
            
            if not anime_items:
                all_links = soup.find_all('a')
                anime_items = [link for link in all_links if '/anime/' in link.get('href', '')]
            
            for item in anime_items[:15]:
                try:
                    if item.name == 'a':
                        link_elem = item
                        title = item.get('title', '').strip() or item.text.strip()
                    else:
                        link_elem = item.find('a')
                        if not link_elem:
                            continue
                        
                        title = ''
                        title_selectors = ['h3', 'h2', 'h4', '.title', 'span']
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
                    
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url and '/anime/' in url and len(title) > 2:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception:
                    continue
            
            return results
            
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            episode_links = soup.find_all('a', href=re.compile(r'/ep/'))
            
            for link in episode_links:
                try:
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_title = link.text.strip()
                    
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
        
        # METODO 1: Cerca tutti gli iframe (anche nascosti)
        all_iframes = soup.find_all('iframe')
        print(f"📺 Found {len(all_iframes)} iframes")
        
        for iframe in all_iframes:
            src = iframe.get('src') or iframe.get('data-src')
            if src:
                print(f"   Checking iframe: {src}")
                
                # FILTRA SOLO PUBBLICITÀ OVVIE
                obvious_ads = ['a-ads.com', 'doubleclick.', 'googlesyndication.']
                if any(ad in src.lower() for ad in obvious_ads):
                    print(f"   ❌ Skipping obvious ad: {src}")
                    continue
                
                # ACCETTA TUTTO IL RESTO
                if not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                
                print(f"   ✅ Adding iframe: {src}")
                streams.append({
                    'url': src,
                    'quality': 'HD',
                    'type': 'iframe'
                })
        
        # METODO 2: Cerca nei script per URL video
        scripts = soup.find_all('script')
        print(f"📜 Found {len(scripts)} scripts")
        
        for script in scripts:
            if script.string and len(script.string) > 50:
                script_content = script.string
                
                # Pattern per trovare URL video
                patterns = [
                    r'(?:src|file|url)["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)',
                    r'["\']([^"\']*(?:stream|video|player)[^"\']*)["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, script_content, re.I)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        if (url and url.startswith('http') and 
                            len(url) > 20 and
                            not any(skip in url.lower() for skip in ['analytics', 'tracker'])):
                            print(f"   ✅ Script URL: {url}")
                            streams.append({
                                'url': url,
                                'quality': 'HD',
                                'type': 'direct'
                            })
        
        # METODO 3: Cerca link diretti nella pagina
        all_links = soup.find_all('a')
        for link in all_links:
            href = link.get('href', '')
            link_text = link.text.strip().lower()
            
            # Cerca link che sembrano video
            if (href and 
                (any(ext in href.lower() for ext in ['.mp4', '.m3u8', '.mkv']) or
                 any(word in link_text for word in ['download', 'scarica', 'guarda', 'stream']))):
                
                if href.startswith('http'):
                    print(f"   ✅ Direct link: {href}")
                    streams.append({
                        'url': href,
                        'quality': 'HD',
                        'type': 'direct'
                    })
        
        # METODO 4: Cerca elementi video/source
        videos = soup.find_all(['video', 'source'])
        for video in videos:
            src = video.get('src')
            if src:
                if not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                print(f"   ✅ Video element: {src}")
                streams.append({
                    'url': src,
                    'quality': 'HD',
                    'type': 'direct'
                })
        
        # METODO 5: Debug - stampa contenuto pagina se non trova nulla
        if not streams:
            print("❌ No streams found, debugging...")
            print(f"Page title: {soup.title.text if soup.title else 'No title'}")
            print(f"Page contains 'player': {'player' in response.text.lower()}")
            print(f"Page contains 'video': {'video' in response.text.lower()}")
            print(f"Page contains 'stream': {'stream' in response.text.lower()}")
            
            # Come ultima risorsa, prendi QUALSIASI iframe
            for iframe in all_iframes:
                src = iframe.get('src') or iframe.get('data-src')
                if src and src.startswith('http'):
                    print(f"   🔄 Fallback iframe: {src}")
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
        
        # Rimuovi duplicati
        seen_urls = set()
        unique_streams = []
        for stream in streams:
            if stream['url'] not in seen_urls:
                seen_urls.add(stream['url'])
                unique_streams.append(stream)
        
        print(f"🎯 AnimeSaturn final streams: {len(unique_streams)}")
        return unique_streams[:5]
        
    except Exception as e:
        print(f"❌ AnimeSaturn stream error: {e}")
        import traceback
        traceback.print_exc()
        return []
