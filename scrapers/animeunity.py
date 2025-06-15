import requests
from bs4 import BeautifulSoup
import json
import re
from urllib.parse import urljoin, quote
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper
from fake_headers import Headers

class AnimeUnityScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "AnimeUnity"
        self.base_url = "https://www.animeunity.so"
        self.enabled = getattr(config, 'AU', '0') == "1"
        self.api_url = f"{self.base_url}/api"
        self.random_headers = Headers()
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            headers = self.random_headers.generate()
            
            # Prova prima con API JSON (come AnimeWorld API)
            try:
                api_search_url = f"{self.api_url}/search"
                params = {'q': query, 'limit': 10}
                response = self.make_request(api_search_url, params=params, headers=headers)
                
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    if 'records' in data and data['records']:
                        results = []
                        for anime in data['records']:
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
                        return results[:10]
            except Exception:
                pass
            
            # Fallback HTML search (come AnimeWorld fallback)
            search_url = f"{self.base_url}/anime"
            params = {'search': query}
            response = self.make_request(search_url, params=params, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            cards = soup.find_all('div', class_='card')
            
            for card in cards[:10]:
                try:
                    link_elem = card.find('a')
                    if not link_elem:
                        continue
                    
                    # Cerca titolo
                    title_elem = card.find('h5', class_='card-title')
                    title = title_elem.text.strip() if title_elem else link_elem.get('title', '').strip()
                    
                    url = urljoin(self.base_url, link_elem.get('href'))
                    
                    # Cerca immagine
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
            
            print(f"🎯 AnimeUnity found {len(results)} results")
            return results
            
        except Exception as e:
            print(f"AnimeUnity search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        # Implementazione simile ad AnimeSaturn ma adattata per AnimeUnity
        if not self.enabled:
            return []
            
        try:
            headers = self.random_headers.generate()
            response = self.make_request(anime_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # AnimeUnity potrebbe avere episodi in script JSON
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string and ('episodes' in script.string or 'episodi' in script.string):
                    try:
                        # Cerca array episodi nel JavaScript
                        episodes_match = re.search(r'episodes["\']?\s*:\s*(\[.*?\])', script.string, re.DOTALL)
                        if episodes_match:
                            episodes_data = json.loads(episodes_match.group(1))
                            for ep in episodes_data:
                                if isinstance(ep, dict):
                                    ep_num = ep.get('number', ep.get('episodio', len(episodes) + 1))
                                    episodes.append({
                                        'number': int(ep_num),
                                        'title': f"Episodio {ep_num}",
                                        'url': f"{anime_url}/episodio-{ep_num}"
                                    })
                            break
                    except:
                        continue
            
            # Fallback: cerca link episodi diretti
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
        # Implementazione simile ad AnimeSaturn
        if not self.enabled:
            return []
            
        try:
            headers = self.random_headers.generate()
            response = self.make_request(episode_url, headers=headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Cerca iframe video
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
            
            print(f"🎯 AnimeUnity found {len(streams)} streams")
            return streams[:5]
            
        except Exception as e:
            print(f"AnimeUnity stream error: {e}")
            return []
