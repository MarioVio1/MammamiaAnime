const BaseScraper = require('./base_scraper');
const cheerio = require('cheerio');

class AnimeUnityScraper extends BaseScraper {
  constructor(config) {
    super(config);
    this.init('AnimeUnity', config.animeunity);
  }

  async search(query) {
    try {
      const encodedQuery = encodeURIComponent(query);
      
      // Prima prova con l'API JSON
      try {
        const apiUrl = `${this.config.animeunity.search_url}?q=${encodedQuery}`;
        const jsonResponse = await this.makeRequest(apiUrl, {
          headers: { ...this.headers, 'Accept': 'application/json' }
        });

        if (typeof jsonResponse === 'object' && jsonResponse.records) {
          return jsonResponse.records.map(anime => ({
            id: anime.id.toString(),
            title: anime.title || anime.title_ita,
            url: `${this.baseUrl}/anime/${anime.id}-${anime.slug}`,
            image: anime.imageurl || anime.cover,
            site: 'animeunity'
          }));
        }
      } catch (apiError) {
        // Fallback HTML se API non funziona
        console.warn(`[${this.name}] API search failed, trying HTML fallback`);
      }

      // ... (fallback HTML)
    } catch (error) {
      console.error(`[${this.name}] Search error:`, error.message);
      return [];
    }
  }

  // ... (altri metodi)
}

module.exports = AnimeUnityScraper;
