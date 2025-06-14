import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
from .base_scraper import BaseScraper

class AnimeSaturnScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeSaturn"
        self.base_url = "https://www.animesaturn.tv"
        self.search_url = f"{self.base_url}/animelist"
        
    def search(self, query):
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
                    image = urljoin(self.base_url, img_elem.get('src', '')) if img_elem else None
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animesaturn'
                        })
                except Exception as e:
                    continue
                    
            return results
        except Exception as e:
            print(f"AnimeSaturn search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            episode_links = soup.find_all('a', href=re.compile(r'/ep/'))
            
            for link in episode_links:
                episode_url = urljoin(self.base_url, link.get('href'))
                episode_title = link.text.strip()
                
                # Estrai numero episodio
                episode_match = re.search(r'episodio[- ](\d+)', episode_title.lower())
                episode_num = int(episode_match.group(1)) if episode_match else len(episodes) + 1
                
                episodes.append({
                    'number': episode_num,
                    'title': episode_title,
                    'url': episode_url
                })
                
            return sorted(episodes, key=lambda x: x['number'])
        except Exception as e:
            print(f"AnimeSaturn episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):
        try:
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Cerca iframe video
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src and ('streamingaw' in src or 'vixcloud' in src or 'streamtape' in src):
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            # Cerca link diretti
            video_tags = soup.find_all('video')
            for video in video_tags:
                sources = video.find_all('source')
                for source in sources:
                    src = source.get('src')
                    if src:
                        streams.append({
                            'url': src,
                            'quality': source.get('data-quality', 'HD'),
                            'type': 'direct'
                        })
            
            return streams
        except Exception as e:
            print(f"AnimeSaturn stream error: {e}")
            return []
