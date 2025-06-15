# File: scrapers/animeunity.py
import requests
import re
import json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
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
        self.headers = {
            'Authorization': f'Bearer {self.access_token}',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
        }

    def _get_access_token(self):
        """Ottieni token JWT dalla pagina principale"""
        try:
            response = requests.get(self.base_url, timeout=10)
            match = re.search(r'window\.accessToken\s*=\s*"([^"]+)"', response.text)
            return match.group(1) if match else None
        except Exception as e:
            print(f"Errore ottenimento token: {e}")
            return None

    def search(self, query):
        if not self.enabled or not self.access_token:
            return []
            
        try:
            params = {
                'q': query,
                'limit': 15,
                'fields': 'id,title,slug,imageurl,type'
            }
            
            response = requests.get(
                f"{self.api_url}/search",
                params=params,
                headers=self.headers
            )
            
            if response.status_code == 200:
                return [{
                    'title': item['title'],
                    'url': f"{self.base_url}/anime/{item['id']}-{item['slug']}",
                    'image': item.get('imageurl'),
                    'site': 'animeunity',
                    'anime_id': item['id'],
                    'type': item['type']
                } for item in response.json().get('records', [])[:10]]
            
            return []
            
        except Exception as e:
            print(f"Errore ricerca AnimeUnity: {e}")
            return []

    def get_episodes(self, anime_url):
        if not self.enabled or not self.access_token:
            return []
            
        try:
            anime_id = re.search(r'/anime/(\d+)', anime_url).group(1)
            
            response = requests.get(
                f"{self.api_url}/anime/{anime_id}/episodes",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return [{
                    'number': ep['number'],
                    'title': f"Episodio {ep['number']}",
                    'url': f"{anime_url}/episodio-{ep['number']}",
                    'episode_id': ep['id']
                } for ep in response.json()[:50]]
                
            return []
            
        except Exception as e:
            print(f"Errore episodi AnimeUnity: {e}")
            return []

    def get_stream_links(self, episode_url):
        if not self.enabled or not self.access_token:
            return []
            
        try:
            episode_id = re.search(r'/episodio-(\d+)', episode_url).group(1)
            
            response = requests.get(
                f"{self.api_url}/episode/{episode_id}/sources",
                headers=self.headers
            )
            
            if response.status_code == 200:
                return [{
                    'url': src['url'],
                    'quality': src.get('quality', 'HD'),
                    'type': 'direct'
                } for src in response.json() if 'scws-content.net' in src['url']]
                
            return []
            
        except Exception as e:
            print(f"Errore stream AnimeUnity: {e}")
            return []
