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
        self.base_url = config.AS_DOMAIN
        self.enabled = config.AS == "1"
        self.search_url = f"{self.base_url}/animelist"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            search_params = {'search': query}
            response = self.make_request(self.search_url, params=search_params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Cerca nella lista anime
            anime_items = soup.find_all('div', class_='item-archivio')
            if not anime_items:
                # Fallback: cerca con selettori alternativi
                anime_items = soup.find_all('a', href=re.compile(r'/anime/'))
            
            for item in anime_items:
                try:
                    if item.name == 'a':
                        link_elem = item
                        title = item.get('title', '').strip() or item.text.strip()
                    else:
                        link_elem = item.find('a')
                        title_elem = item.find('h3') or item.find('h2') or item.find('.title')
                        title = title_elem.text.strip() if title_elem else ''
                        
                    if not link_elem:
                        continue
                        
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Cerca immagine
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src:
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url and '/anime/' in url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception as e:
                    print(f"Error parsing AnimeSaturn item: {e}")
                    continue
                    
            # Se non trova risultati, prova ricerca diretta
            if not results:
                results = self._search_direct(query)
                    
            return results[:10]  # Limita a 10 risultati
            
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            return []
    
    def _search_direct(self, query):
        """Ricerca diretta nella homepage o sezioni popolari"""
        try:
            response = self.make_request(self.base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Cerca in tutte le sezioni anime
            anime_links = soup.find_all('a', href=re.compile(r'/anime/'))
            
            for link in anime_links:
                title = link.get('title', '') or link.text.strip()
                if query.lower() in title.lower():
                    url = urljoin(self.base_url, link.get('href'))
                    
                    # Cerca immagine associata
                    img = link.find('img') or link.find_next('img')
                    image = None
                    if img:
                        img_src = img.get('src') or img.get('data-src')
                        if img_src:
                            image = urljoin(self.base_url, img_src)
                    
                    results.append({
                        'title': title,
                        'url': url,
                        'image': image,
                        'site': 'animesaturn'
                    })
                    
                    if len(results) >= 5:
                        break
                        
            return results
            
        except Exception as e:
            print(f"AnimeSaturn direct search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Cerca lista episodi
            episode_links = soup.find_all('a', href=re.compile(r'/ep/'))
            if not episode_links:
                # Fallback: cerca con pattern alternativi
                episode_links = soup.find_all('a', href=re.compile(r'episodio'))
            
            for link in episode_links:
                try:
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_title = link.text.strip()
                    
                    # Estrai numero episodio
                    episode_match = re.search(r'(?:episodio[- ]?|ep[- ]?)(\d+)', episode_title.lower())
                    if episode_match:
                        episode_num = int(episode_match.group(1))
                    else:
                        # Fallback: usa posizione nell'array
                        episode_num = len(episodes) + 1
                    
                    episodes.append({
                        'number': episode_num,
                        'title': episode_title or f"Episodio {episode_num}",
                        'url': episode_url
                    })
                    
                except Exception as e:
                    print(f"Error parsing episode: {e}")
                    continue
                    
            # Ordina per numero episodio
            episodes = sorted(episodes, key=lambda x: x['number'])
            
            # Se non trova episodi, crea un episodio singolo
            if not episodes:
                episodes = [{
                    'number': 1,
                    'title': 'Episodio 1',
                    'url': anime_url
                }]
                
            return episodes
            
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
        
        # METODO 1: Cerca iframe video
        iframes = soup.find_all('iframe')
        print(f"📺 Found {len(iframes)} iframes")
        
        for iframe in iframes:
            src = iframe.get('src')
            if src:
                print(f"   Iframe src: {src}")
                if any(host in src.lower() for host in ['vixcloud', 'streamingaw', 'streamtape', 'mixdrop', 'doodstream']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
        
        # METODO 2: Cerca video tag diretti
        video_tags = soup.find_all('video')
        print(f"🎥 Found {len(video_tags)} video tags")
        
        for video in video_tags:
            sources = video.find_all('source')
            for source in sources:
                src = source.get('src')
                if src:
                    print(f"   Video src: {src}")
                    streams.append({
                        'url': src,
                        'quality': source.get('data-quality', 'HD'),
                        'type': 'direct'
                    })
        
        # METODO 3: Cerca nei script JavaScript
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string:
                # Cerca pattern comuni per URL video
                video_patterns = [
                    r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                    r'https?://[^\s"\']+\.(?:mp4|m3u8|mkv)',
                ]
                
                for pattern in video_patterns:
                    matches = re.findall(pattern, script.string, re.I)
                    for match in matches:
                        url = match if isinstance(match, str) else match[0]
                        if url and url.startswith('http'):
                            print(f"   Script URL: {url}")
                            streams.append({
                                'url': url,
                                'quality': 'HD',
                                'type': 'direct'
                            })
        
        print(f"🎯 Total streams found: {len(streams)}")
        return streams[:5]  # Limita a 5 stream
        
    except Exception as e:
        print(f"❌ AnimeSaturn stream error: {e}")
        return []

