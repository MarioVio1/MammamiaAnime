const BaseScraper = require('./base_scraper');
const cheerio = require('cheerio');

class AnimeSaturnScraper extends BaseScraper {
  constructor(config) {
    super(config);
    this.init('AnimeSaturn', config.animesaturn);
  }

  async search(query) {
    try {
      const encodedQuery = encodeURIComponent(query);
      const searchUrl = `${this.baseUrl}/search?q=${encodedQuery}`;
      
      const html = await this.makeRequest(searchUrl);
      const $ = cheerio.load(html);
      const results = [];

      $(this.selectors.search_results).each((index, element) => {
        const $el = $(element);
        const title = $el.find(this.selectors.anime_title).text().trim();
        const link = $el.find(this.selectors.anime_link).attr('href');
        const image = $el.find('img').attr('src');
        
        if (title && link) {
          results.push({
            id: this.extractIdFromUrl(link),
            title: title,
            url: link.startsWith('http') ? link : this.baseUrl + link,
            image: image ? (image.startsWith('http') ? image : this.baseUrl + image) : null,
            site: 'animesaturn'
          });
        }
      });

      return results;
    } catch (error) {
      console.error(`[${this.name}] Search error:`, error.message);
      return [];
    }
  }

  // ... (altri metodi per episodi e stream)
}

module.exports = AnimeSaturnScraper;
