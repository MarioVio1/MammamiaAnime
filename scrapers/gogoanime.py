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
        self.base_url = config.GA_DOMAIN
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
            
            # Se non trova risultati, prova ricerca alternativa
            if not results:
                results = self._search_alternative(query)
                    
            return results
            
        except Exception as e:
            print(f"GogoAnime search error: {e}")
            return []
    
    def _search_alternative(self, query):
        """Ricerca alternativa nella homepage o sezioni popolari"""
        try:
            response = self.make_request(self.base_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            # Cerca in tutte le sezioni anime
            anime_links = soup.find_all('a', href=re.compile(r'/category/'))
            
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
                        'site': 'gogoanime'
                    })
                    
                    if len(results) >= 5:
                        break
                        
            return results
            
        except Exception as e:
            print(f"GogoAnime alternative search error: {e}")
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
                            for ep_num in range(start_num, min(end_num + 1, start_num + 50)):  # Limita a 50 episodi per range
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
            
            # Metodo 3: Cerca nella lista episodi della sidebar
            if not episodes:
                episode_list = soup.find('div', class_='anime_video_body') or soup.find('ul', class_='episodes-list')
                if episode_list:
                    episode_links = episode_list.find_all('a')
                    for i, link in enumerate(episode_links):
                        href = link.get('href', '')
                        if 'episode' in href:
                            ep_match = re.search(r'(\d+)', href)
                            ep_num = int(ep_match.group(1)) if ep_match else i + 1
                            episode_url = urljoin(self.base_url, href)
                            
                            episodes.append({
                                'number': ep_num,
                                'title': f"Episode {ep_num}",
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
            return episodes[:100]  # Limita a 100 episodi
            
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
                        'type': 'iframe',
                        'server': self._extract_server_name(src)
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
                        'type': 'direct',
                        'server': 'Direct'
                    })
            
            # Metodo 3: Cerca nei script per link nascosti
            scripts = soup.find_all('script')
            for script in scripts:
                if script.string:
                    # Pattern per trovare URL video
                    patterns = [
                        r'(?:file|src|url)["\']?\s*:\s*["\']([^"\']+\.(?:mp4|m3u8|mkv))["\']',
                        r'https?://[^\s"\']+\.(?:mp4|m3u8|mkv)',
                        r'["\']([^"\']*(?:gogo|vidstreaming|streamani)[^"\']*)["\']'
                    ]
                    
                    for pattern in patterns:
                        matches = re.findall(pattern, script.string, re.I)
                        for match in matches:
                            url = match if isinstance(match, str) else match[0]
                            if url and url.startswith('http'):
                                streams.append({
                                    'url': url,
                                    'quality': 'HD',
                                    'type': 'direct',
                                    'server': 'Script'
                                })
            
            # Metodo 4: Cerca server alternativi nella pagina
            server_links = soup.find_all('a', class_=re.compile(r'server|quality'))
            for link in server_links:
                href = link.get('href')
                if href:
                    if not href.startswith('http'):
                        href = urljoin(self.base_url, href)
                    
                    # Prova a estrarre stream da server alternativi
                    try:
                        server_streams = self._extract_from_server(href)
                        streams.extend(server_streams)
                    except:
                        continue
            
            # Rimuovi duplicati e limita risultati
            seen_urls = set()
            unique_streams = []
            for stream in streams:
                if stream['url'] not in seen_urls and len(unique_streams) < 5:
                    seen_urls.add(stream['url'])
                    unique_streams.append(stream)
            
            return unique_streams
            
        except Exception as e:
            print(f"GogoAnime stream error: {e}")
            return []
    
    def _extract_from_server(self, server_url):
        """Estrae stream da server alternativi"""
        try:
            response = self.make_request(server_url)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            streams = []
            
            # Cerca iframe nel server alternativo
            iframes = soup.find_all('iframe')
            for iframe in iframes:
                src = iframe.get('src')
                if src:
                    if not src.startswith('http'):
                        src = urljoin(server_url, src)
                    
                    streams.append({
                        'url': src,
                        'quality': 'HD',
                        'type': 'iframe',
                        'server': 'Alt Server'
                    })
            
            return streams
            
        except:
            return []
    
    def _extract_server_name(self, url):
        """Estrae il nome del server dall'URL"""
        url_lower = url.lower()
        if 'gogo' in url_lower:
            return 'GogoAnime'
        elif 'vidstreaming' in url_lower:
            return 'VidStreaming'
        elif 'streamani' in url_lower:
            return 'StreamAni'
        elif 'mp4upload' in url_lower:
            return 'Mp4Upload'
        elif 'doodstream' in url_lower:
            return 'DoodStream'
        else:
            return 'Unknown'
