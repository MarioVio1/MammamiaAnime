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
            anime_items = soup.find_all('div', class_='item-archivio')
            
            for item in anime_items:
                try:
                    link_elem = item.find('a')
                    if not link_elem:
                        continue
                        
                    title = link_elem.get('title', '').strip()
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src:
                            image = urljoin(self.base_url, img_src)
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                        
                except Exception as e:
                    continue
                    
            return results[:10]
            
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
                    
                except Exception as e:
                    continue
                    
            return sorted(episodes, key=lambda x: x['number'])
            
        except Exception as e:
            print(f"AnimeSaturn episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):  # ← LINEA 173 CORRETTA
        if not self.enabled:  # ← INDENTAZIONE CORRETTA
            return []
            
        try:
            print(f"🔗 Getting streams from: {episode_url}")
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Cerca iframe video
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
            
            # Cerca video tag diretti
            video_tags = soup.find_all('video')
            for video in video_tags:
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src')
                    if src:
                        if not src.startswith('http'):
                            src = urljoin(self.base_url, src)
                        
                        streams.append({
                            'url': src,
                            'quality': source.get('data-quality', 'HD'),
                            'type': 'direct'
                        })
            
            print(f"🎯 Total streams found: {len(streams)}")
            return streams[:5]
            
        except Exception as e:
            print(f"AnimeSaturn stream error: {e}")
            return []
