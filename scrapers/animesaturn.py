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
            
            # Selettori aggiornati per AnimeSaturn 2025
            selectors_to_try = [
                'div.item-archivio',
                'div.anime-item',
                'div.card',
                '.anime-card',
                'a[href*="/anime/"]',
                'div[class*="anime"]',
                'li[class*="item"]',
                'div[class*="item"]'
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
                    continue
            
            if not anime_items:
                print("❌ No items found with any selector, trying fallback...")
                all_links = soup.find_all('a')
                anime_items = [link for link in all_links if '/anime/' in link.get('href', '')]
                print(f"🔄 Fallback found {len(anime_items)} anime links")
            
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
                    
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src') or img_elem.get('data-lazy')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
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
            print(f"📺 Getting AnimeSaturn episodes from: {anime_url}")
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
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
                    print(f"✅ Found {len(links)} episodes with selector: {selector}")
                    episode_links = links
                    break
            
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
            
            print(f"📺 AnimeSaturn found {len(episodes)} episodes")
            return sorted(episodes, key=lambda x: x['number'])
            
        except Exception as e:
            print(f"AnimeSaturn episodes error: {e}")
            return []
    
def get_stream_links(self, episode_url):
    if not self.enabled:
        return []
        
    try:
        print(f"🔗 Getting AnimeSaturn streams from: {episode_url}")
        response = self.make_request(episode_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        streams = []
        
        # METODO 1: Cerca player video principale
        video_player = soup.find('div', id='player')
        if video_player:
            player_iframes = video_player.find_all('iframe')
            for iframe in player_iframes:
                src = iframe.get('src')
                if src and not any(ad in src.lower() for ad in ['ads', 'ad.']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    print(f"   ✅ Player iframe: {src}")
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
        
        # METODO 2: Cerca tutti gli iframe (FILTRATO)
        all_iframes = soup.find_all('iframe')
        print(f"📺 Found {len(all_iframes)} total iframes")
        
        for iframe in all_iframes:
            src = iframe.get('src')
            if src:
                print(f"   Checking iframe: {src}")
                
                # FILTRA PUBBLICITÀ E TRACKER
                skip_domains = [
                    'a-ads.com', 'ads.', 'adnxs.', 'doubleclick.', 'googlesyndication.',
                    'googletagmanager.', 'facebook.com/tr', 'google-analytics.',
                    'analytics.', 'tracker.', 'pixel.', 'beacon.'
                ]
                
                if any(skip in src.lower() for skip in skip_domains):
                    print(f"   ❌ Skipping: {src}")
                    continue
                
                # ACCETTA IFRAME CON DIMENSIONI VIDEO
                width = iframe.get('width', '0')
                height = iframe.get('height', '0')
                if width and height:
                    try:
                        w, h = int(width), int(height)
                        if w >= 400 and h >= 200:  # Dimensioni minime video
                            if not src.startswith('http'):
                                src = urljoin(self.base_url, src)
                            
                            print(f"   ✅ Video iframe ({w}x{h}): {src}")
                            streams.append({
                                'url': src,
                                'quality': 'HD',
                                'type': 'iframe'
                            })
                    except:
                        pass
        
        # METODO 3: Cerca link download diretti
        download_links = soup.find_all('a', string=re.compile(r'download|scarica|guarda', re.I))
        for link in download_links:
            href = link.get('href')
            if href and any(ext in href.lower() for ext in ['.mp4', '.m3u8', '.mkv']):
                print(f"   ✅ Download link: {href}")
                streams.append({
                    'url': href,
                    'quality': 'HD',
                    'type': 'direct'
                })
        
        # METODO 4: Cerca nei script per URL video
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and len(script.string) > 100:  # Solo script sostanziali
                # Pattern per video URL
                video_patterns = [
                    r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                    r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv)',
                    r'["\']([^"\']*(?:streamingaw|animeworld|vixcloud)[^"\']*)["\']'
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        if (url and url.startswith('http') and 
                            not any(skip in url.lower() for skip in ['ads', 'analytics', 'tracker'])):
                            print(f"   ✅ Script video: {url}")
                            streams.append({
                                'url': url,
                                'quality': 'HD',
                                'type': 'direct'
                            })
        
        # METODO 5: Se non trova nulla, cerca qualsiasi iframe non pubblicitario
        if not streams:
            print("🔄 No streams found, trying all non-ad iframes...")
            for iframe in all_iframes:
                src = iframe.get('src')
                if (src and src.startswith('http') and 
                    not any(ad in src.lower() for ad in ['ads', 'ad.', 'analytics'])):
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
        
        print(f"🎯 AnimeSaturn found {len(unique_streams)} unique streams")
        return unique_streams[:5]
        
    except Exception as e:
        print(f"❌ AnimeSaturn stream error: {e}")
        import traceback
        traceback.print_exc()
        return []
