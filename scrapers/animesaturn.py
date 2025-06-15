import requests
from bs4 import BeautifulSoup
import re
import datetime
from urllib.parse import urljoin, quote
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper
from fake_headers import Headers

class AnimeSaturnScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeSaturn"
        self.base_url = "https://www.animesaturn.cx"
        self.enabled = getattr(config, 'AS', '0') == "1"
        self.random_headers = Headers()
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            # Usa la stessa strategia di AnimeWorld
            headers = self.random_headers.generate()
            
            # AnimeSaturn ha una ricerca diretta
            search_url = f"{self.base_url}/animelist"
            params = {'search': query}
            
            response = self.make_request(search_url, params=params, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Cerca con selettori specifici per AnimeSaturn
            anime_cards = soup.find_all('div', class_='item-archivio')
            
            for card in anime_cards[:10]:
                try:
                    link_elem = card.find('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get('title', '').strip()
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Cerca immagine come in AnimeWorld
                    img_elem = card.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url and '/anime/' in url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception as e:
                    continue
            
            print(f"🎯 AnimeSaturn found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            headers = self.random_headers.generate()
            response = self.make_request(anime_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # AnimeSaturn ha link episodi diretti
            episode_links = soup.find_all('a', href=re.compile(r'/ep/'))
            
            for link in episode_links:
                try:
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_title = link.text.strip()
                    
                    # Estrai numero episodio come in AnimeWorld
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
            headers = self.random_headers.generate()
            response = self.make_request(episode_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # METODO 1: Cerca download link diretto (come AnimeWorld)
            download_link = soup.find('a', {'id': 'alternativeDownloadLink'})
            if download_link:
                url = download_link.get('href')
                if url:
                    # Verifica che il link funzioni
                    test_response = requests.head(url, timeout=5)
                    if test_response.status_code != 404:
                        streams.append({
                            'url': url,
                            'quality': 'HD',
                            'type': 'direct'
                        })
            
            # METODO 2: Cerca iframe come AnimeWorld
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and any(host in src.lower() for host in ['vixcloud', 'streamingaw', 'animeworld']):
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            # METODO 3: Cerca nei script (come AnimeWorld)
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Pattern per trovare URL video
                    video_patterns = [
                        r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                        r'https?://[^\s"\']+\.(?:mp4|m3u8|mkv)'
                    ]
                    
                    for pattern in video_patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if url and url.startswith('http'):
                                streams.append({
                                    'url': url,
                                    'quality': 'HD',
                                    'type': 'direct'
                                })
            
            print(f"🎯 AnimeSaturn found {len(streams)} streams")
            return streams[:5]
            
        except Exception as e:
            print(f"AnimeSaturn stream error: {e}")
            return []
