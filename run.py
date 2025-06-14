from fastapi import FastAPI, HTTPException,Request
from fastapi.responses import JSONResponse,RedirectResponse,HTMLResponse
from Src.API.filmpertutti import filmpertutti
from  Src.API.streamingcommunity import streaming_community
from  Src.API.tantifilm import tantifilm
from  Src.API.lordchannel import lordchannel
from  Src.API.streamingwatch import streamingwatch
from Src.API.ddlstream import ddlstream
from Src.API.cb01 import cb01
from Src.API.guardaserie import guardaserie
from Src.API.guardahd import guardahd
import  Src.Utilities.config as config
import logging
from Src.API.okru import okru_get_url
from Src.API.animeworld import animeworld

# NUOVE IMPORTAZIONI ANIME CON FALLBACK SICURO
try:
    from scrapers.animesaturn import AnimeSaturnScraper
    from scrapers.animeunity import AnimeUnityScraper
    from scrapers.gogoanime import GogoAnimeScraper
    ANIME_SCRAPERS_AVAILABLE = True
    print("✅ Anime scrapers loaded successfully")
except ImportError as e:
    print(f"⚠️ Anime scrapers not available: {e}")
    ANIME_SCRAPERS_AVAILABLE = False

from Src.Utilities.dictionaries import okru,STREAM,extra_sources,webru_vary,webru_dlhd,provider_map,skystreaming
from Src.API.epg import tivu, tivu_get,epg_guide,convert_bho_1,convert_bho_2,convert_bho_3
from Src.API.webru import webru,get_skystreaming
from Src.API.onlineserietv import onlineserietv
from curl_cffi.requests import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from static.static import HTML
from urllib.parse import unquote
from Src.Utilities.m3u8 import router as m3u8_clone
import urllib.parse
import re
import asyncio

#Configure Env Vars
Global_Proxy = config.Global_Proxy
if Global_Proxy == "1":
    from Src.Utilities.loadenv import load_env
    env_vars = load_env()
    PROXY_CREDENTIALS = env_vars.get('PROXY_CREDENTIALS')
    proxies = {
    "http": PROXY_CREDENTIALS,
    "https": PROXY_CREDENTIALS
}
else:
    proxies = {}

# Configure config
MYSTERIUS = config.MYSTERIUS
DLHD = config.DLHD
SC = config.SC
SC_DOMAIN = config.SC_DOMAIN
FT = config.FT
TF = config.TF
LC = config.LC
SW = config.SW
AW = config.AW
SKY = config.SKY
CB = config.CB
DDL = config.DDL
GS = config.GS
GHD = config.GHD
OST = config.OST
HOST = config.HOST
PORT = int(config.PORT)
Icon = config.Icon
Name = config.Name
SKY_DOMAIN = config.SKY_DOMAIN
Remote_Instance = config.Remote_Instance

# CONFIGURAZIONI ANIME CON FALLBACK
AS = getattr(config, 'AS', '0')
AU = getattr(config, 'AU', '0')
GA = getattr(config, 'GA', '0')

# AGGIORNA PROVIDER_MAP SE NECESSARIO
if ANIME_SCRAPERS_AVAILABLE:
    provider_map.update({
        'AS': 'ANIMESATURN',
        'AU': 'ANIMEUNITY', 
        'GA': 'GOGOANIME'
    })

# INIZIALIZZAZIONE SCRAPERS ANIME
anime_scrapers = {}
if ANIME_SCRAPERS_AVAILABLE:
    try:
        if AS == "1":
            anime_scrapers['animesaturn'] = AnimeSaturnScraper()
        if AU == "1":
            anime_scrapers['animeunity'] = AnimeUnityScraper()
        if GA == "1":
            anime_scrapers['gogoanime'] = GogoAnimeScraper()
        print(f"🎌 Anime scrapers initialized: {list(anime_scrapers.keys())}")
    except Exception as e:
        print(f"❌ Error initializing anime scrapers: {e}")
        anime_scrapers = {}

#Cool code to set the hugging face if the service is hosted there.
if MYSTERIUS == "1":
    from Src.API.cool import cool
DDL_DOMAIN = config.DDL_DOMAIN
app = FastAPI()
app.include_router(m3u8_clone)
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
User_Agent= "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0"

# MANIFEST ORIGINALE CON AGGIUNTA ANIME
MANIFEST = {
    "id": "org.stremio.mammamia",
    "version": "1.6.0",  # Incrementata per i nuovi scrapers
    "catalogs": [
        {
            "type": "tv",
            "id": "tv_channels",
            "name": "MammaMia",
            "behaviorHints": {
                "configurable": True,
                "configurationRequired": True
                },
            "extra": [
                {
                    "name": "genre",
                    "isRequired": False,
                    "options": ["Rai", "Mediaset", "Sky", "Euronews", "La7", "Warner Bros", "FIT", "Sportitalia","RSI","DAZN", "Rakuten", "Pluto", "A+E", "Paramount", "Chill"]
                }
            ]
        }
    ],
    "resources": ["stream", "catalog", "meta"],
    "types": ["movie", "series", "tv"],
    "name": Name,
    "description": "Addon providing HTTPS Streams for Italian Movies, Series, Live TV and Anime from multiple sources!",
    "logo": "https://creazilla-store.fra1.digitaloceanspaces.com/emojis/49647/pizza-emoji-clipart-md.png"
}

# AGGIUNGI CATALOGHI ANIME SE DISPONIBILI
if anime_scrapers:
    MANIFEST["catalogs"].extend([
        {
            "type": "series",
            "id": "anime_search",
            "name": "Cerca Anime",
            "extra": [
                {
                    "name": "search",
                    "isRequired": True
                }
            ]
        }
    ])

def respond_with(data):
    resp = JSONResponse(data)
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers['Access-Control-Allow-Headers'] = '*'
    return resp

async def transform_mfp(mfp_stream_url,client):
    try:
        response = await client.get(mfp_stream_url)
        data = response.json()
        url = data['mediaflow_proxy_url'] + "?api_password=" + data['query_params']['api_password'] + "&d=" + urllib.parse.quote(data['destination_url'])
        for i in data['request_headers']:
            url += f"&h_{i}={urllib.parse.quote(data['request_headers'][i])}"
        return url
    except Exception as e:
        print("Transforing MFP failed",e)
        return None

# FUNZIONI ANIME
async def search_anime_multi_source(query: str):
    """Cerca anime su tutti i siti configurati"""
    if not anime_scrapers:
        return []
        
    all_results = []
    
    async def search_site(site_name, scraper):
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(None, scraper.search, query)
            for result in results:
                result['source_site'] = site_name
            return results
        except Exception as e:
            print(f"Error searching {site_name}: {e}")
            return []
    
    tasks = [search_site(site_name, scraper) for site_name, scraper in anime_scrapers.items()]
    if tasks:
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)
    
    return all_results

def deduplicate_anime_results(results):
    """Rimuove duplicati basandosi sul titolo normalizzato"""
    seen = {}
    unique_results = []
    
    for result in results:
        normalized_title = re.sub(r'[^\w\s]', '', result['title'].lower()).strip()
        normalized_title = re.sub(r'\s+', ' ', normalized_title)
        
        if normalized_title not in seen:
            seen[normalized_title] = result
            unique_results.append(result)
    
    return unique_results

@app.get('/config')
def config():
    return RedirectResponse(url="/")

@app.get('/{config:path}/manifest.json')
def addon_manifest(config: str): 
    manifest_copy = MANIFEST.copy()  
    if "LIVETV"  in config:
        return respond_with(manifest_copy)
    elif "LIVETV" not in config:
        # Mantieni cataloghi anime se presenti
        if not anime_scrapers:
            manifest_copy["catalogs"] = []
            if "catalog" in manifest_copy["resources"]:
                manifest_copy["resources"].remove("catalog")
        else:
            # Rimuovi solo cataloghi TV, mantieni anime
            manifest_copy["catalogs"] = [cat for cat in manifest_copy["catalogs"] if cat["type"] != "tv"]
        return respond_with(manifest_copy)

@app.get('/manifest.json')
def manifest():
    return RedirectResponse(url="/|SC|LC|SW|/manifest.json")

@app.get('/', response_class=HTMLResponse)
def root(request: Request):
    forwarded_proto = request.headers.get("x-forwarded-proto")
    scheme = forwarded_proto if forwarded_proto else request.url.scheme
    instance_url = f"{scheme}://{request.url.netloc}"
    html_content = HTML.replace("{instance_url}", instance_url)
    return html_content

async def addon_catalog(type: str, id: str, genre: str = None, search: str = None):
    if type == "tv":
        catalogs = {"metas": []}
        
        for channel in STREAM["channels"]:
            if genre and genre not in channel.get("genres", []):
                continue
            
            description = f'Watch {channel["title"]}'
            catalogs["metas"].append({
                "id": channel["id"],
                "type": "tv",
                "name": channel["title"],
                "poster": channel["poster"],
                "description": description,
                "genres": channel.get("genres", [])
            })

        return catalogs
    
    # GESTIONE CATALOGHI ANIME
    elif type == "series" and id.startswith("anime_") and anime_scrapers:
        catalogs = {"metas": []}
        
        if id == "anime_search" and search:
            anime_results = await search_anime_multi_source(search)
            anime_results = deduplicate_anime_results(anime_results)
            
            for anime in anime_results[:15]:
                anime_id = f"anime_{anime['source_site']}_{anime['title'].replace(' ', '_').lower()}"
                anime_id = re.sub(r'[^\w_]', '', anime_id)
                
                catalogs["metas"].append({
                    "id": anime_id,
                    "type": "series",
                    "name": anime['title'],
                    "poster": anime.get('image'),
                    "description": f"Anime da {anime['source_site'].upper()}",
                    "genres": ["Anime"]
                })
        
        return catalogs
    else:
        raise HTTPException(status_code=404)

@app.get('/{config:path}/catalog/{type}/{id}.json')
@limiter.limit("5/second")
async def first_catalog(request: Request,type: str, id: str, genre: str = None):
    search = request.query_params.get('search')
    catalogs = await addon_catalog(type, id, genre, search)
    return respond_with(catalogs)

@app.get('/{config:path}/catalog/{type}/{id}/genre={genre}.json')
async def catalog_with_genre(type: str, id: str, genre: str = None):
    catalogs = await addon_catalog(type, id, genre)
    return respond_with(catalogs)

@app.get('/{config:path}/catalog/{type}/{id}/search={search}.json')
async def catalog_with_search(request: Request, type: str, id: str, search: str):
    catalogs = await addon_catalog(type, id, search=search)
    return respond_with(catalogs)

@app.get('/{config:path}/meta/tv/{id}.json')
@limiter.limit("20/second")
async def addon_meta(request: Request,id: str):
    # Find the channel by ID
    channel = next((ch for ch in STREAM['channels'] if ch['id'] == id), None)
    
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    async with AsyncSession(proxies = proxies) as client:
        if channel["id"] in convert_bho_1 or channel["id"] in convert_bho_2 or channel["id"] in convert_bho_3:
            description,title =  await epg_guide(channel["id"],client)
        elif channel["id"] in tivu:
            description = await tivu_get(channel["id"],client)
            print(description)
            title = ""
        else:
            description = f'Watch {channel["title"]}'
            title = ""
    meta = {
        'meta': {
            'id': channel['id'],
            'type': 'tv',
            'name': channel['name'],
            'poster': channel['poster'],
            'posterShape': 'landscape',
            'description': title + "\n" + description,
            # Additional fields can be added here
            'background': channel['poster'],  # Example of using the same poster as background
            'logo': channel['poster'],
            'genres': channel.get('genres', []),  # Example of using the same poster as logo
        }
    }
    if 'url' in channel:
        meta['meta']['url'] = channel['url']  # Using the stream URL as a website link
    return respond_with(meta)

# NUOVO ENDPOINT META PER ANIME
@app.get('/{config:path}/meta/series/{id}.json')
@limiter.limit("20/second")
async def anime_meta(request: Request, id: str):
    if id.startswith('anime_') and anime_scrapers:
        parts = id.split('_')
        if len(parts) >= 3:
            source_site = parts[1]
            anime_title = ' '.join(parts[2:]).replace('_', ' ').title()
            
            meta = {
                'meta': {
                    'id': id,
                    'type': 'series',
                    'name': anime_title,
                    'poster': None,
                    'description': f"Anime disponibile su {source_site.upper()}",
                    'genres': ['Anime']
                }
            }
            return respond_with(meta)
    
    raise HTTPException(status_code=404, detail="Anime not found")

@app.get('/{config:path}/stream/{type}/{id}.json')
@limiter.limit("5/second")
async def addon_stream(request: Request,config, type, id,):
    if type not in MANIFEST['types']:
        raise HTTPException(status_code=404)
    streams = {'streams': []}
    
    # GESTIONE STREAM ANIME
    if type == "series" and id.startswith('anime_') and anime_scrapers:
        try:
            parts = id.split('_')
            if len(parts) >= 3:
                source_site = parts[1]
                anime_title = ' '.join(parts[2:]).replace('_', ' ')
                
                if source_site in anime_scrapers:
                    scraper = anime_scrapers[source_site]
                    loop = asyncio.get_event_loop()
                    
                    search_results = await loop.run_in_executor(None, scraper.search, anime_title)
                    if search_results:
                        anime_url = search_results[0]['url']
                        episodes = await loop.run_in_executor(None, scraper.get_episodes, anime_url)
                        
                        if episodes:
                            first_episode = episodes[0]
                            stream_links = await loop.run_in_executor(None, scraper.get_stream_links, first_episode['url'])
                            
                            for stream in stream_links:
                                streams['streams'].append({
                                    'name': f"{Name} - {source_site.upper()}",
                                    'title': f'{Icon}{source_site.upper()} - {stream.get("quality", "HD")}',
                                    'url': stream['url'],
                                    'behaviorHints': {
                                        'notWebReady': stream.get('type') == 'iframe',
                                        'bingeGroup': f'anime_{source_site}'
                                    }
                                })
            
            if not streams['streams']:
                streams['streams'].append({
                    'title': f'{Icon}Anime non disponibile',
                    'url': 'https://example.com/not_found.mp4'
                })
                
        except Exception as e:
            print(f"Error getting anime streams: {e}")
            raise HTTPException(status_code=404)
            
        return respond_with(streams)
    
    # CODICE ORIGINALE INVARIATO
    if "|" in config:
        config_providers = config.split('|')
    elif "%7C" in config:
        config_providers = config.split('%7C')
    provider_maps = {name: "0" for name in provider_map.values()}
    for provider in config_providers:
            if provider in provider_map:
                provider_name = provider_map[provider]
                provider_maps[provider_name] = "1"
    if "MFP[" in config:
    # Extract proxy data between "MFP(" and ")"
        mfp_data = config.split("MFP[")[1].split(")")[0]  
    # Split the data by comma to get proxy URL and password
        MFP_url, MFP_password = mfp_data.split(",")
        MFP_password = MFP_password[:-2]
    # Store them in a list
        MFP_CREDENTIALS = [MFP_url, MFP_password]
        if MFP_url and MFP_password:
            MFP = "1"
    else:
        MFP = "0"
    async with AsyncSession(proxies = proxies) as client:
        if type == "tv":
            for channel in STREAM["channels"]:
                if channel["id"] == id:
                    i = 0
                    if 'url' in channel:
                        i = i+1
                        streams['streams'].append({
                            'title': f"{Icon}Server {i} " + f" "+ channel['name'] + " " + channel['title'] ,
                            'url': channel['url']
                            })     
                    if id in okru:
                        i = i+1
                        channel_url = await okru_get_url(id,client)
                        streams['streams'].append({'title':  f"{Icon}Server {i} " +  channel['title'] + " OKRU",'url': channel_url,  "behaviorHints": {"notWebReady": True, "proxyHeaders": {"request": {"User-Agent": User_Agent}}}})
                    if id in extra_sources:
                        list_sources = extra_sources[id]
                        for item in list_sources:
                            i = i+1
                            if "iran" in item:
                                streams['streams'].append({'title':f"{Icon}Server {i} " + channel['title'],'url': item, "behaviorHints": {"notWebReady": True, "proxyHeaders": {"request": {"Origin": "https://babaktv.com", "Referer": "https://babaktv.com/"}}}})
                            else:
                                streams['streams'].append({'title':f"{Icon}Server {i} " + channel['title'],'url': item})
                    if id in skystreaming and SKY == "1":
                        url,Host,Sky_Origin = await get_skystreaming(id,client)
                        i = i+1
                        if url:
                            streams['streams'].append({'title': f'{Icon}Server S {i}' + channel['title'], 'url': url, "behaviorHints": {"notWebReady": True, "proxyHeaders": {"request": {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.5", "Origin": Sky_Origin, "DNT": "1", "Sec-GPC": "1", "Connection": "keep-alive", "Referer": f"{Sky_Origin}/", "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "cross-site", "Pragma": "no-cache", "Cache-Control": "no-cache", "TE": "trailers","Host": Host}}}})
                    if id in webru_vary:
                        i = i+1
                        webru_url, Referer_webru_url,Origin_webru_url = await webru(id,"vary",client)
                        if MFP== "1" and webru_url:
                            webru_url = f'{MFP_url}/proxy/hls/manifest.m3u8?api_password={MFP_password}&d={webru_url}&h_Referer={Referer_webru_url}&h_Origin={Origin_webru_url}&h_User-Agent=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F58.0.3029.110%20Safari%2F537.3'
                            streams['streams'].append({'title': f"{Icon}Proxied Server X-{i} " + channel['title'],'url': webru_url})
                        else:
                            if webru_url:
                                streams['streams'].append({'title': f'{Icon}Server X-{i}' + channel['title'], 'url': webru_url, "behaviorHints": {"notWebReady": True, "proxyHeaders": {"request": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.5", "Origin": Origin_webru_url, "DNT": "1", "Sec-GPC": "1", "Connection": "keep-alive", "Referer": Referer_webru_url, "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "cross-site", "Pragma": "no-cache", "Cache-Control": "no-cache", "TE": "trailers"}}}})

                    if id in webru_dlhd:
                        if DLHD == "1":
                            i = i+1
                            webru_url_2,Referer_webru_url_2,Origin_webru_url_2 = await webru(id,"dlhd",client)
                            if MFP== "1":
                                webru_url_2 = f'{MFP_url}/proxy/hls/manifest.m3u8?api_password={MFP_password}&d={webru_url_2}&h_Referer={Referer_webru_url_2}&h_Origin={Origin_webru_url_2}&h_User-Agent=Mozilla%2F5.0%20(Windows%20NT%2010.0%3B%20Win64%3B%20x64)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F58.0.3029.110%20Safari%2F537.3'
                                streams['streams'].append({'title': f"{Icon}Proxied Server D-{i} " + channel['title'],'url': webru_url_2})
                            else:
                                streams['streams'].append({'title': f'{Icon}Server D-{i}' + channel['title'], 'url': webru_url_2, "behaviorHints": {"notWebReady": True, "proxyHeaders": {"request": {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3", "Accept": "*/*", "Accept-Language": "en-US,en;q=0.5", "Origin": Origin_webru_url_2, "DNT": "1", "Sec-GPC": "1", "Connection": "keep-alive", "Referer": Referer_webru_url_2, "Sec-Fetch-Dest": "empty", "Sec-Fetch-Mode": "cors", "Sec-Fetch-Site": "cross-site", "Pragma": "no-cache", "Cache-Control": "no-cache", "TE": "trailers"}}}})

            if not streams['streams']:
                raise HTTPException(status_code=404)
            return respond_with(streams)
        elif "tt" in id or "tmdb" in id or "kitsu" in id:
            
            print(f"Handling movie or series: {id}")
            if "kitsu" in id:
                if provider_maps['ANIMEWORLD'] == "1" and AW == "1":
                    animeworld_urls = await animeworld(id,client)
                    if animeworld_urls:
                        print(f"AnimeWorld Found Results for {id}")
                        i = 0
                        for url in animeworld_urls:
                            if url:
                                if i == 0:
                                    title = "Original"
                                elif i == 1:
                                     title = "Italian"
                                streams['streams'].append({'title': f'{Icon}Animeworld {title}', 'url': url})
                                i+=1
            else:
                import time
                current_time = int(time.time())
                if 1743487223 <= current_time <= 1743544823:
                    streams['streams'].append({'name': f"{Name} 4K",'title': f'{Icon}Netflix/Prime Extractor 4K', 'url': "https://cdn-cf-east.streamable.com/video/mp4/jkx9gr.mp4?Expires=1743457311748&Key-Pair-Id=APKAIEYUVEN4EVB2OKEQ&Signature=gpixXPFJb5huM8D6AMkbzNqmAON-9zBUVIN5AeWcHiXBVROSz6BlmctAVx0qpe-hM1DN3OO7YtIdBKKOk3IthF33agmVmVjSyNI-emjf~iuqxclbaousBJTPXMIjDQTxBxINr0SUbyS4MiIwhar~luiqqvbPHN9jS-AXT2r1chhZylE4Zol~bKSCCT10TzN3En630XMk0UiTFCgwoAxfitI4mnuCXu4M3-mcnN~kpxx9j6VgE0jVzBKFq9qYbi-CtWOCL7mVaVaCwrTPPe9syZVQgIlgQJt175raLM2G2~faR~wuDOda7KmGNJJH2hDfdd~-sPsr6SSNV0B9ZZ3eaw__"})
                if MYSTERIUS == "1":
                    results = await cool(id,client)
                    if results:
                        print(f"Mysterius Found Results for {id}")
                        for resolution, link in results.items():
                            streams['streams'].append({'title': f'{Icon}Mysterious {resolution}', 'url': link, 'behaviorHints': {'bingeGroup': f'mysterius{resolution}'}})
                if provider_maps['STREAMINGCOMMUNITY'] == "1" and SC == "1":
                    SC_FAST_SEARCH = provider_maps['SC_FAST_SEARCH']
                    url_streaming_community,quality_sc, slug_sc = await streaming_community(id,client,SC_FAST_SEARCH,MFP)
                    if url_streaming_community is not None:
                        print(f"StreamingCommunity Found Results for {id}")
                        if MFP == "1":
                            url_streaming_community = f'{MFP_url}/extractor/video?api_password={MFP_password}&d={url_streaming_community}&host=VixCloud&redirect_stream=false'
                            url_streaming_community = await transform_mfp(url_streaming_community,client)
                            if "hf.space" in MFP_url:
                                streams['streams'].append({"name":f'{Name}', 'title': f'{Icon}StreamingCommunity\n Sorry StreamingCommunity wont work, most likely, with MFP hosted on HuggingFace','url': url_streaming_community})

                            streams['streams'].append({"name":f'{Name}\n{quality_sc} Max', 'title': f'{Icon}StreamingCommunity\n {slug_sc.replace("-"," ").capitalize()}','url': url_streaming_community,'behaviorHints':{'notWebReady': False, 'bingeGroup': f'streamingcommunity{quality_sc}'}})
                        else:
                            streams['streams'].append({"name":f'{Name}\n{quality_sc}p Max', 'title': f'{Icon}StreamingCommunity\n {slug_sc.replace("-"," ").capitalize()}\n This will work only on a local instance','url': url_streaming_community,'behaviorHints': {'proxyHeaders': {"request": {"user-agent": User_Agent}}, 'notWebReady': True, 'bingeGroup': f'streamingcommunity{quality_sc}'}})
                
                if provider_maps['LORDCHANNEL'] == "1" and LC == "1":
                    url_lordchannel,quality_lordchannel = await lordchannel(id,client)
                    if quality_lordchannel == "FULL HD" and url_lordchannel !=  None:
                        print(f"LordChannel Found Results for {id}")
                        streams['streams'].append({'name': f"{Name}\n1080p",'title': f'{Icon}LordChannel', 'url': url_lordchannel,'behaviorHints': {'bingeGroup': 'lordchannel1080'}})
                    elif url_lordchannel !=  None:
                        print(f"LordChannel Found Results for {id}")
                        streams['streams'].append({"name": f"{Name}\n720p",'title': f'{Icon}LordChannel 720p', 'url': url_lordchannel, 'behaviorHints': {'bingeGroup': 'lordchannel720'}})            
                if provider_maps['FILMPERTUTTI'] == "1" and FT == "1":
                    url_filmpertutti,Host = await filmpertutti(id,client, MFP)
                    if url_filmpertutti is not None and Host is not None:
                        if MFP == "1":
                            url_filmpertutti = f'{MFP_url}/extractor/video?api_password={MFP_password}&d={url_filmpertutti}&host={Host}&redirect_stream=true'
                            print(url_filmpertutti)
                            streams['streams'].append({'name': f'{Name}', 'title': f'{Icon}Filmpertutti', 'url': url_filmpertutti,'behaviorHints': {'bingeGroup': 'filmpertutti'}})
                        else:
                            streams['streams'].append({'name': f'{Name}', 'title': f'{Icon}Filmpertutti', 'url': url_filmpertutti,'behaviorHints': {'proxyHeaders': {"request": {"User-Agent": "Mozilla/5.0 (Windows NT 10.10; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"}}, 'notWebReady': True, 'bingeGroup': 'filmpertutti'}})
                        print(f"Filmpertutti Found Results for {id}")
                        
                if provider_maps['TANTIFILM'] == "1" and TF == "1":
                    TF_FAST_SEARCH = provider_maps['TF_FAST_SEARCH']                    
                    url_tantifilm = await tantifilm(id,client,TF_FAST_SEARCH)
                    if url_tantifilm != "{'Doodstream HD': None}" and url_tantifilm != None:
                        print(f"TantiFilm Found Results for {id}")
                        if not isinstance(url_tantifilm, str):
                            for title, url in url_tantifilm.items():    
                                streams['streams'].append({'title': f'{Icon}Tantifilm {title}', 'url': url,  'behaviorHints': {'proxyHeaders': {"request": {"Referer": "https://d000d.com/"}}, 'notWebReady': True, 'bingeGroup': f'tantifilm{title}'}})
                        else:
                            streams['streams'].append({'title': f'{Icon}Tantifilm', 'url': url_tantifilm,  'behaviorHints': {'proxyHeaders': {"request": {"Referer": "https://d000d.com/"}}, 'notWebReady': True, 'bingeGroup': 'tantifilm'}})
                if provider_maps['STREAMINGWATCH'] == "1" and SW == "1":
                    url_streamingwatch,Referer = await streamingwatch(id,client)
                    if url_streamingwatch: 
                        print(f"StreamingWatch Found Results for {id}")
                        streams['streams'].append({'name': f"{Name}\n720/1080p",'title': f'{Icon}StreamingWatch', 'url': url_streamingwatch,  'behaviorHints': {'proxyHeaders': {"request": {"Referer": Referer}}, 'notWebReady': True, 'bingeGroup': 'streamingwatch'}})
                if provider_maps['DDLSTREAM'] == "1" and DDL == "1":
                    if MFP == "1":
                        results = await ddlstream(id,client)
                        if  results:
                            print(f"DDLStreamItaly Found Results for {id}")
                            url_ddlstream = results[0]
                            quality = results[1]
                            name = unquote(url_ddlstream.split('/')[-1].replace(".mp4",""))
                            url_ddlstream = f'{MFP_url}/proxy/stream?api_password={MFP_password}&d={url_ddlstream}&h_Referer=https://ddlstreamitaly.{DDL_DOMAIN}/'
                            streams['streams'].append({'name': f"{Name}\n{quality}",'title': f'{Icon}DDLStream \n {name}', 'url': url_ddlstream, 'behaviorHints': {'bingeGroup': 'ddlstream'}}) 
                if provider_maps['CB01'] == "1" and CB == "1":
                    url_cbo1 = await cb01(id,client,MFP)
                    if url_cbo1:
                        print(f"CB01 Found Results for {id}")
                        if "mixdrop" in url_cbo1:
                            if MFP == "1":
                                url_cbo1 = f'{MFP_url}/extractor/video?api_password={MFP_password}&d={url_cbo1}&host=Mixdrop&redirect_stream=false'
                                url_cbo1 = await transform_mfp(url_cbo1,client)
                                if url_cbo1:
                                    streams['streams'].append({'name': f"{Name}",'title': f'{Icon}CB01', 'url': url_cbo1, 'behaviorHints': {'bingeGroup': 'cb01'}})
                        elif "delivery" in url_cbo1:
                            streams['streams'].append({'name': f'{Name}', 'title': f'{Icon}CB01\n MixDrop Will work only on a local instance!', 'url': url_cbo1,'behaviorHints': {'proxyHeaders': {"request": {"User-Agent": User_Agent}}, 'notWebReady': True, 'bingeGroup': 'cb01'}})

                        else:
                            streams['streams'].append({'name': f"{Name}",'title': f'{Icon}CB01\n MaxStream', 'url': url_cbo1, 'behaviorHints': {'bingeGroup': 'cb01'}})
            if provider_maps['GUARDASERIE'] == "1" and GS == "1":
                url_guardaserie = await guardaserie(id,client)
                if url_guardaserie:
                    print(f"Guardaserie Found Results for {id}")
                    streams['streams'].append({'name': f"{Name}",'title': f'{Icon}Guardaserie', 'url': url_guardaserie, 'behaviorHints': {'bingeGroup': 'guardaserie'}})
            if provider_maps['GUARDAHD'] == "1" and GHD == "1":
                url_guardahd = await guardahd(id,client)
                if url_guardahd:
                    print(f"GuardaHD Found Results for {id}")
                    streams['streams'].append({'name': f"{Name}",'title': f'{Icon}GuardaHD', 'url': url_guardahd, 'behaviorHints': {'bingeGroup': 'guardahd'}})
            if provider_maps['ONLINESERIETV'] == "1" and OST == "1":
                url_onlineserietv,name = await onlineserietv(id,client)
                if url_onlineserietv:
                    print(f"OnlineSerieTV Found Results for {id}")
                    streams['streams'].append({'name': f"{Name}",'title': f'{Icon}OnlineSerieTV\n{name}', 'url': url_onlineserietv, 'behaviorHints': {'proxyHeaders': {'request': {"User-Agent": 'Mozilla/5.0 (Linux; Android 12) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.5060.71 Mobile Safari/537.36', "Referer": "https://flexy.stream/"}}, 'bingeGroup': 'onlineserietv', 'notWebReady': True}})
            
        if not streams['streams']:
            raise HTTPException(status_code=404)

    return respond_with(streams)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run("run:app", host=HOST, port=PORT, log_level="info")
