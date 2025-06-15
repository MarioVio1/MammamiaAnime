import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, quote, parse_qs, urlparse
import Src.Utilities.config as config
from scrapers.base_scraper import BaseScraper

class GogoAnimeScraper(BaseScraper):
    def __init__(self):
        super().__init__()
        self.name = "GogoAnime"
        self.base_url = "https://www.anitaku.to"
        self.enabled = config.GA == "1"
        
    def search(self, query):
        if not self.enabled:
            return []
            
        try:
            search_url = f"{self.base_url}/search.html"
            params = {'keyword': query}
            response = self.make_request(search_url, params=params)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            
            # Cerca risultati di ricerca con vari selettori
            selectors = [
                '.items li',
                '.anime_list_body li',
                'ul.items li',
                'li'
            ]
            
            anime_items = []
            for selector in selectors:
                anime_items = soup.select(selector)
                if anime_items:
                    # Filtra solo elementi che contengono link anime
                    anime_items = [item for item in anime_items if item.find('a', href=re.compile(r'/category/'))]
                    if anime_items:
                        break
            
            for item in anime_items[:10]:
                try:
                    # Cerca link principale
                    link_elem = item.find('a', href=re.compile(r'/category/'))
                    if not link_elem:
                        continue
                    
                    # Cerca titolo con vari metodi
                    title = ''
                    title_elem = item.find('a', class_='ss-title')
                    if title_elem:
                        title = title_elem.text.strip()
                    else:
                        title = link_elem.get('title', '').strip()
                        if not title:
                            title = link_elem.text.strip()
                    
                    if not title:
                        continue
                    
                    url = urljoin(self.base_url, link_elem.get('href', ''))
                    
                    # Cerca immagine
                    img_elem = item.find('img')
                    image = None
                    if img_elem:
                        img_src = img_elem.get('src') or img_elem.get('data-src')
                        if img_src and not img_src.startswith('data:'):
                            image = urljoin(self.base_url, img_src)
                    
                    # Verifica che sia un link anime valido
                    if '/category/' in url and query.lower() in title.lower():
                        results.append({
                            'title': title,
                            'url': url,
                            'image': image,
                            'site': 'gogoanime'
                        })
                        
                except Exception as e:
                    print(f"Error parsing GogoAnime item: {e}")
                    continue
            
            return results
            
        except Exception as e:
            print(f"GogoAnime search error: {e}")
            return []
    
    def get_episodes(self, anime_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(anime_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            episodes = []
            
            # Metodo 1: Cerca lista episodi con AJAX
            episode_page = soup.find('ul', id='episode_page')
            if episode_page:
                episode_links = episode_page.find_all('a')
                anime_id = anime_url.split('/category/')[-1]
                
                for link in episode_links:
                    ep_start = link.get('ep_start')
                    ep_end = link.get('ep_end')
                    
                    if ep_start and ep_end:
                        try:
                            start_num = int(ep_start)
                            end_num = int(ep_end)
                            
                            # Genera episodi per il range
                            for ep_num in range(start_num, min(end_num + 1, start_num + 50)):
                                episode_url = f"{self.base_url}/{anime_id}-episode-{ep_num}"
                                episodes.append({
                                    'number': ep_num,
                                    'title': f"Episode {ep_num}",
                                    'url': episode_url
                                })
                        except ValueError:
                            continue
            
            # Metodo 2: Cerca link episodi diretti
            if not episodes:
                episode_links = soup.find_all('a', href=re.compile(r'-episode-\d+'))
                for link in episode_links:
                    href = link.get('href', '')
                    match = re.search(r'-episode-(\d+)', href)
                    if match:
                        ep_num = int(match.group(1))
                        episode_url = urljoin(self.base_url, href)
                        title = link.text.strip() or f"Episode {ep_num}"
                        
                        episodes.append({
                            'number': ep_num,
                            'title': title,
                            'url': episode_url
                        })
            
            # Se non trova episodi, crea un episodio singolo
            if not episodes:
                episodes = [{
                    'number': 1,
                    'title': 'Episode 1',
                    'url': anime_url.replace('/category/', '/')
                }]
            
            # Ordina e limita episodi
            episodes = sorted(episodes, key=lambda x: x['number'])
            return episodes[:100]
            
        except Exception as e:
            print(f"GogoAnime episodes error: {e}")
            return []
    
    def get_stream_links(self, episode_url):
        if not self.enabled:
            return []
            
        try:
            response = self.make_request(episode_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Metodo 1: Cerca iframe video principali
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src:
                    if not src.startswith('http'):
                        src = urljoin(self.base_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe'
                    })
            
            # Metodo 2: Cerca link di download/streaming alternativi
            download_links = soup.find_all('a', href=re.compile(r'\.(?:mp4|m3u8|mkv)'))
            for link in download_links:
                href = link.get('href')
                if href and href.startswith('http'):
                    quality = link.text.strip() if link.text.strip() else 'HD'
                    streams.append({
                        'url': href,
                        'quality': quality,
                        'type': 'direct'
                    })
            
            return streams[:5]
            
        except Exception as e:
            print(f"GogoAnime stream error: {e}")
            return []
