import requests
from bs4 import BeautifulSoup
import re
import base64
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
            page_content = response.text
            
            # Cerca URL nei script JavaScript
            scripts = soup.find_all('script')
            
            for script in scripts:
                if script.string and len(script.string) > 100:
                    script_content = script.string
                    
                    patterns = [
                        r'(?:file|src|url|video)["\']?\s*[:=]\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                        r'["\']([^"\']*(?:vixcloud|streamingaw|animeworld|mixdrop|doodstream)[^"\']*)["\']',
                        r'https?://[^\s"\'<>]+/[^\s"\'<>]*(?:stream|video|play|watch)[^\s"\'<>]*',
                        r'atob\(["\']([^"\']+)["\']',
                        r'iframe[^>]*src["\']?\s*[:=]\s*["\']([^"\']+)["\']'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script_content, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if (url and len(url) > 15 and
                                not any(skip in url.lower() for skip in ['ads', 'analytics', 'tracker', 'pixel'])):
                                
                                if pattern.startswith('atob'):
                                    try:
                                        url = base64.b64decode(url).decode('utf-8')
                                    except:
                                        continue
                                
                                if url.startswith('//'):
                                    url = 'https:' + url
                                elif url.startswith('/'):
                                    url = self.base_url + url
                                
                                if url.startswith('http'):
                                    streams.append({
                                        'url': url,
                                        'quality': 'HD',
                                        'type': 'iframe' if 'iframe' in pattern else 'direct'
                                    })
            
            # Cerca tutti gli iframe
            all_iframes = soup.find_all('iframe')
            for iframe in all_iframes:
                src = iframe.get('src') or iframe.get('data-src') or iframe.get('data-lazy-src')
                if src:
                    if not any(ad in src.lower() for ad in ['a-ads.com', 'doubleclick.', 'googlesyndication.']):
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif not src.startswith('http'):
                            src = urljoin(self.base_url, src)
                        
                        streams.append({
                            'url': src,
                            'quality': 'HD',
                            'type': 'iframe'
                        })
            
            # Se non trova nulla, cerca qualsiasi URL che potrebbe essere video
            if not streams:
                all_urls = re.findall(r'https?://[^\s"\'<>]+', page_content)
                video_urls = [url for url in all_urls if 
                             any(hint in url.lower() for hint in ['stream', 'video', 'play', 'embed', 'watch']) and
                             not any(skip in url.lower() for skip in ['ads', 'analytics', 'tracker'])]
                
                for url in video_urls[:3]:
                    streams.append({
                        'url': url,
                        'quality': 'HD',
                        'type': 'direct'
                    })
            
            # Rimuovi duplicati
            seen_urls = set()
            unique_streams = []
            for stream in streams:
                if stream['url'] not in seen_urls:
                    seen_urls.add(stream['url'])
                    unique_streams.append(stream)
            
            print(f"🎯 AnimeSaturn found {len(unique_streams)} streams")
            return unique_streams[:5]
            
        except Exception as e:
            print(f"❌ AnimeSaturn stream error: {e}")
            return []
