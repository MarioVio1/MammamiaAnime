import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote
from .base_scraper import BaseScraper

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = "https://www.animeunity.to"
        self.api_url = f"{self.base_url}/api"
        
    def search(self, query):
        try:
            # Prova prima con API
            try:
                api_search_url = f"{self.api_url}/search"
                params = {'q': query}
                response = self.make_request(api_search_url, params=params)
                
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    if 'records' in data:
                        results = []
                        for anime in data['records']:
                            results.append({
                                'title': anime.get('title', anime.get('title_ita', '')),
                                'url': f"{self.base_url}/anime/{anime['id']}-{anime.get('slug', '')}",
                                'image': anime.get('imageurl', anime.get('cover')),
                                'site': 'animeunity'
                            })
                        return results
            except:
                pass
            
            # Fallback HTML
            search_url = f"{self.base_url}/anime"
            params = {'search': query}
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            anime_cards = soup.find_all('div', class_='card')
            
            for card in anime_cards:
                try:
                    link_elem = card.find('a')
                    if not link_elem:
                        continue
                        
                    title_elem = card.find('h5', class_='card-title')
                    title = title_elem.text.strip() if title_elem else ''
                    
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    img_elem = card.find('img')
                    image = img_elem.get('src') if img_elem else None
                    
                    if title and url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'animeunity'
                        })
                except Exception:
                    continue
                    
            return results
        except Exception as e:
            print(f"AnimeUnity search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Cerca script con dati episodi
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and 'episodes' in script.string:
                    # Estrai JSON con episodi
                    match = re.search(r'episodes["\']:\s*(\[.*?\])', script.string)
                    if match:
                        try:
                            episodes_data = json.loads(match.group(1))
                            for ep in episodes_data:
                                episodes.append({
                                    'number': ep.get('number', 1),
                                    'title': f"Episodio {ep.get('number', 1)}",
                                    'url': f"{anime_url}/episodio-{ep.get('number', 1)}"
                                })
                        except:
                            pass
            
            # Fallback: cerca link episodi
            if not episodes:
                episode_links = soup.find_all('a', href=re.compile(r'/episodio-'))
                for i, link in enumerate(episode_links):
                    episode_url = urljoin(self.base_url, link.get('href'))
                    episode_num = i + 1
                    
                    episodes.append({
                        'number': episode_num,
                        'title': f"Episodio {episode_num}",
                        'url': episode_url
                    })
            
            return sorted(episodes, key=lambda x: x['number'])
        except Exception as e:
            print(f"AnimeUnity episodes error: {e}")
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
                if src and any(host in src for host in ['vixcloud', 'streamingaw', 'animeworld']):
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            return streams
        except Exception as e:
            print(f"AnimeUnity stream error: {e}")
            return []
