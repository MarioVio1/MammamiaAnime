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
        
        # FILTRI PER ESCLUDERE URL NON VIDEO
        exclude_patterns = [
            r'\.css',
            r'\.js',
            r'\.woff',
            r'\.ttf',
            r'\.png',
            r'\.jpg',
            r'\.gif',
            r'fonts\.googleapis\.com',
            r'analytics',
            r'tracker',
            r'ads',
            r'facebook\.com',
            r'google-analytics',
            r'googletagmanager'
        ]
        
        def is_valid_video_url(url):
            """Verifica se l'URL è potenzialmente un video"""
            if not url or len(url) < 20:
                return False
            
            # Escludi URL non video
            for pattern in exclude_patterns:
                if re.search(pattern, url, re.I):
                    return False
            
            # Accetta solo URL che sembrano video
            video_indicators = [
                r'\.mp4',
                r'\.m3u8',
                r'\.mkv',
                r'\.avi',
                r'vixcloud',
                r'streamingaw',
                r'animeworld',
                r'mixdrop',
                r'doodstream',
                r'streamtape',
                r'fembed',
                r'supervideo',
                r'/stream',
                r'/video',
                r'/play',
                r'/embed',
                r'/watch'
            ]
            
            return any(re.search(indicator, url, re.I) for indicator in video_indicators)
        
        # METODO 1: Cerca URL nei script JavaScript
        scripts = soup.find_all('script')
        
        for script in scripts:
            if script.string and len(script.string) > 100:
                script_content = script.string
                
                # Pattern per URL video
                patterns = [
                    r'(?:file|src|url|video)["\']?\s*[:=]\s*["\']([^"\']+)["\']',
                    r'https?://[^\s"\'<>]+\.(?:mp4|m3u8|mkv|avi)',
                    r'["\']([^"\']*(?:vixcloud|streamingaw|animeworld|mixdrop|doodstream)[^"\']*)["\']'
                ]
                
                for pattern in patterns:
                    matches = re.findall(pattern, script_content, re.I)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        
                        # Completa URL relativi
                        if url.startswith('//'):
                            url = 'https:' + url
                        elif url.startswith('/'):
                            url = self.base_url + url
                        
                        if url.startswith('http') and is_valid_video_url(url):
                            print(f"   ✅ Valid script URL: {url}")
                            streams.append({
                                'url': url,
                                'quality': 'HD',
                                'type': 'direct'
                            })
        
        # METODO 2: Cerca iframe video (FILTRATI)
        all_iframes = soup.find_all('iframe')
        for iframe in all_iframes:
            src = iframe.get('src') or iframe.get('data-src')
            if src:
                # Completa URL
                if src.startswith('//'):
                    src = 'https:' + src
                elif not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                
                if is_valid_video_url(src):
                    print(f"   ✅ Valid iframe: {src}")
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
        
        # METODO 3: Cerca link download specifici
        download_links = soup.find_all('a', string=re.compile(r'download|scarica|guarda|stream|play', re.I))
        for link in download_links:
            href = link.get('href')
            if href and is_valid_video_url(href):
                if not href.startswith('http'):
                    href = urljoin(self.base_url, href)
                
                print(f"   ✅ Valid download link: {href}")
                streams.append({
                    'url': href,
                    'quality': 'HD',
                    'type': 'direct'
                })
        
        # METODO 4: Cerca video/source tag
        video_elements = soup.find_all(['video', 'source'])
        for element in video_elements:
            src = element.get('src')
            if src and is_valid_video_url(src):
                if not src.startswith('http'):
                    src = urljoin(self.base_url, src)
                
                print(f"   ✅ Valid video element: {src}")
                streams.append({
                    'url': src,
                    'quality': element.get('data-quality', 'HD'),
                    'type': 'direct'
                })
        
        # Rimuovi duplicati
        seen_urls = set()
        unique_streams = []
        for stream in streams:
            if stream['url'] not in seen_urls:
                seen_urls.add(stream['url'])
                unique_streams.append(stream)
        
        print(f"🎯 AnimeSaturn found {len(unique_streams)} valid video streams")
        
        # Se non trova video reali, non restituire nulla
        if not unique_streams:
            print("❌ No valid video streams found")
        
        return unique_streams[:5]
        
    except Exception as e:
        print(f"❌ AnimeSaturn stream error: {e}")
        return []
