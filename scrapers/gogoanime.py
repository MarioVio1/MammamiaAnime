import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, quote
from .base_scraper import BaseScraper

class GogoAnimeScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "GogoAnime"
        self.base_url = "https://gogoanime3.co"
        
    def search(self, query):
        try:
            search_url = f"{self.base_url}/search.html"
            params = {'keyword': query}
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            anime_items = soup.find_all('li')
            
            for item in anime_items:
                try:
                    link_elem = item.find('a')
                    if not link_elem:
                        continue
                        
                    title_elem = item.find('a', class_='ss-title')
                    title = title_elem.text.strip() if title_elem else link_elem.get('title', '').strip()
                    
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    img_elem = item.find('img')
                    image = img_elem.get('src') if img_elem else None
                    
                    if title and url and '/category/' in url:
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'gogoanime'
                        })
                except Exception:
                    continue
                    
            return results
        except Exception as e:
            print(f"GogoAnime search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Cerca lista episodi
            episode_page = soup.find('ul', id='episode_page')
            if episode_page:
                episode_links = episode_page.find_all('a')
                for link in episode_links:
                    ep_start = link.get('ep_start')
                    ep_end = link.get('ep_end')
                    
                    if ep_start and ep_end:
                        # Genera episodi per range
                        anime_id = anime_url.split('/category/')[-1]
                        for ep_num in range(int(ep_start), int(ep_end) + 1):
                            episode_url = f"{self.base_url}/{anime_id}-episode-{ep_num}"
                            episodes.append({
                                'number': ep_num,
                                'title': f"Episode {ep_num}",
                                'url': episode_url
                            })
            
            return sorted(episodes, key=lambda x: x['number'])
        except Exception as e:
            print(f"GogoAnime episodes error: {e}")
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
                if src:
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            return streams
        except Exception as e:
            print(f"GogoAnime stream error: {e}")
            return []
