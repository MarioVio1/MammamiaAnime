# File: scrapers/animeunity.py
import requests
import json
import re
from urllib.parse import urljoin
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = "https://www.animeunity.so"
        self.api_url = f"{self.base_url}/api"
        self.enabled = getattr(config, 'AU', '0') == "1"
        self.access_token = self._get_access_token()

    def _get_access_token(self):
        """Ottieni token JWT per le richieste API"""
        try:
            response = requests.get(self.base_url, timeout=10)
            match = re.search(r'window\.accessToken\s*=\s*"([^"]+)"', response.text)
            return match.group(1) if match else None
        except:
            return None

    def search(self, query):
        if not self.enabled or not self.access_token:
            return []
            
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        try:
            # API diretta per la ricerca
            response = requests.get(
                f"{self.api_url}/search",
                params={'q': query, 'limit': 10},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                return [{
                    'title': item['title'],
                    'url': f"{self.base_url}/anime/{item['id']}",
                    'image': item.get('imageurl'),
                    'site': 'animeunity'
                } for item in data.get('records', [])[:10]]
            
            return []
            
        except Exception as e:
            print(f"AnimeUnity API error: {e}")
            return []

    def get_episodes(self, anime_url):
        if not self.enabled or not self.access_token:
            return []
            
        try:
            anime_id = re.search(r'/anime/(\d+)', anime_url).group(1)
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Fetch episodi via API
            response = requests.get(
                f"{self.api_url}/anime/{anime_id}/episodes",
                headers=headers
            )
            
            if response.status_code == 200:
                episodes = response.json()
                return [{
                    'number': ep['number'],
                    'title': f"Episodio {ep['number']}",
                    'url': f"{anime_url}/episodio-{ep['number']}"
                } for ep in episodes[:100]]
                
            return []
            
        except Exception as e:
            print(f"AnimeUnity episodes error: {e}")
            return []

    def get_stream_links(self, episode_url):
        if not self.enabled or not self.access_token:
            return []
            
        try:
            # Estrai ID episodio
            episode_id = re.search(r'/episodio-(\d+)', episode_url).group(1)
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'X-Requested-With': 'XMLHttpRequest'
            }
            
            # Fetch stream diretto
            response = requests.get(
                f"{self.api_url}/episode/{episode_id}/sources",
                headers=headers
            )
            
            if response.status_code == 200:
                sources = response.json()
                return [{
                    'url': src['url'],
                    'quality': src.get('quality', 'HD'),
                    'type': 'direct'
                } for src in sources if 'scws-content.net' in src['url']]
                
            return []
            
        except Exception as e:
            print(f"AnimeUnity stream error: {e}")
            return []
