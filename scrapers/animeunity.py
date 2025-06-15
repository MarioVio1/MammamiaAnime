import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote, urlparse, parse_qs
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = "https://www.animeunity.so"
        self.enabled = getattr(config, 'AU', '0') == "1"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            # AnimeUnity ha API di ricerca
            search_url = f"{self.base_url}/api/search"
            params = {'q': query}
            
            response = self.make_request(search_url, params=params)
            
            # Verifica se è JSON
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                results = []
                
                for anime in data.get('records', []):
                    anime_id = anime.get('id')
                    slug = anime.get('slug', '')
                    title = anime.get('title', anime.get('title_ita', ''))
                    
                    if anime_id and title:
                        results.append({
                            'title': title,
                            'url': f"{self.base_url}/anime/{anime_id}-{slug}",
                            'image': anime.get('imageurl', anime.get('cover')),
                            'site': 'animeunity',
                            'anime_id': anime_id
                        })
                
                print(f"🎯 AnimeUnity API found {len(results)} results")
                return results[:10]
            
            # Fallback HTML se API non funziona
            return self._search_html(query)
            
        except Exception as e:
            print(f"AnimeUnity search error: {e}")
            return self._search_html(query)
    
    def _search_html(self, query):
        """Ricerca HTML fallback"""
        try:
            search_url = f"{self.base_url}/anime"
            params = {'search': query}
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            cards = soup.find_all('div', class_='card')
            
            for card in cards[:10]:
                try:
                    link = card.find('a')
                    if not link:
                        continue
                    
                    title_elem = card.find('h5', class_='card-title')
                    title = title_elem.text.strip() if title_elem else link.get('title', '').strip()
                    
                    url = urljoin(self.base_url, link.get('href'))
                    
                    img_elem = card.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animeunity'
                        })
                        
                except Exception:
                    continue
            
            print(f"🎯 AnimeUnity HTML found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"AnimeUnity HTML search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # METODO 1: Cerca episodi in script JSON
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('episodes' in script.string or 'episodi' in script.string):
                    try:
                        # Cerca array episodi nel JavaScript
                        episodes_patterns = [
                            r'episodes["\']?\s*:\s*(\[.*?\])',
                            r'episodi["\']?\s*:\s*(\[.*?\])',
                            r'var\s+episodes\s*=\s*(\[.*?\]);',
                            r'let\s+episodes\s*=\s*(\[.*?\]);'
                        ]
                        
                        for pattern in episodes_patterns:
                            match = re.search(pattern, script.string, re.DOTALL)
                            if match:
                                episodes_data = json.loads(match.group(1))
                                for ep in episodes_data:
                                    if isinstance(ep, dict):
                                        ep_num = ep.get('number', ep.get('episodio', len(episodes) + 1))
                                        episodes.append({
                                            'number': int(ep_num),
                                            'title': f"Episodio {ep_num}",
                                            'url': f"{anime_url}/episodio-{ep_num}"
                                        })
                                    elif isinstance(ep, (int, str)):
                                        episodes.append({
                                            'number': int(ep),
                                            'title': f"Episodio {ep}",
                                            'url': f"{anime_url}/episodio-{ep}"
                                        })
                                break
                    except:
                        continue
                    
                    if episodes:
                        break
            
            # METODO 2: Cerca link episodi diretti
            if not episodes:
                episode_links = soup.find_all('a', href=re.compile(r'/episodio-'))
                for link in episode_links:
                    href = link.get('href', '')
                    ep_match = re.search(r'episodio-(\d+)', href)
                    if ep_match:
                        ep_num = int(ep_match.group(1))
                        episode_url = urljoin(self.base_url, href)
                        episodes.append({
                            'number': ep_num,
                            'title': f"Episodio {ep_num}",
                            'url': episode_url
                        })
            
            return sorted(episodes, key=lambda x: x['number'])[:100]
            
        except Exception as e:
            print(f"AnimeUnity episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):
        if not self.enabled:
            return []
            
        try:
            print(f"🔗 Getting AnimeUnity streams from: {episode_url}")
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # METODO 1: Cerca link diretti MP4 nei script
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Pattern per trovare link scws-content.net (dal risultato [1])
                    patterns = [
                        r'https://[^"\']*\.scws-content\.net/[^"\']*\.mp4[^"\']*',
                        r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']*scws-content[^"\']*)["\']',
                        r'["\']([^"\']*au-d\d+-\d+\.scws-content\.net[^"\']*)["\']'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if url and url.startswith('http') and 'scws-content.net' in url:
                                print(f"   ✅ Found AnimeUnity MP4: {url}")
                                
                                # Estrai qualità dal path (1080p, 720p, etc.)
                                quality = 'HD'
                                if '1080p' in url:
                                    quality = '1080p'
                                elif '720p' in url:
                                    quality = '720p'
                                elif '480p' in url:
                                    quality = '480p'
                                
                                streams.append({
                                    'url': url,
                                    'quality': quality,
                                    'type': 'direct'
                                })
            
            # METODO 2: Cerca iframe video
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and any(host in src.lower() for host in ['animeunity', 'scws-content']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            # METODO 3: Cerca video tag diretti
            video_tags = soup.find_all('video')
            for video in video_tags:
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src')
                    if src and 'scws-content.net' in src:
                        streams.append({
                            'url': src,
                            'quality': source.get('data-quality', 'HD'),
                            'type': 'direct'
                        })
            
            print(f"🎯 AnimeUnity found {len(streams)} streams")
            return streams[:5]
            
        except Exception as e:
            print(f"❌ AnimeUnity stream error: {e}")
            return []
