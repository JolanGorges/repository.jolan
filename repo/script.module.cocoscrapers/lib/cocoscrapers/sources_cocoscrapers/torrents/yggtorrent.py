import re
from urllib.parse import quote_plus, unquote_plus
from requests.utils import requote_uri
from cocoscrapers.modules import client
from cocoscrapers.modules import source_utils
from cocoscrapers.modules import workers

class source:
	priority = 8
	pack_capable = True
	hasMovies = True
	hasEpisodes = True
	def __init__(self):
		self.language = ['fr']
		self.base_link = "https://www3.yggtorrent.cool"
		self.search_link = '/engine/search?name=%s&category=2145&sub_category=all&do=search&order=desc&sort=size'
		self.min_seeders = 0

	def sources(self, data, hostDict):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		self.items = []
		self.items_append = self.items.append
		try:
			self.aliases = data['aliases']
			self.year = data['year']
			if 'tvshowtitle' in data:
				self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ').replace('$', 's')
				self.episode_title = data['title']
				self.hdlr = 'S%02dE%02d' % (int(data['season']), int(data['episode']))
			else:
				self.title = data['title'].replace('&', 'and').replace('/', ' ').replace('$', 's')
				self.episode_title = None
				self.hdlr = self.year
			queries = [self.get_query(self.title, self.hdlr)]
			if data['aliases'] and data['aliases'][0]['country'] == 'fr':
				queries.append(self.get_query(data['aliases'][0]['title'], self.hdlr))

			urls = []
			for query in queries:
				url = '%s%s' % (self.base_link, self.search_link % query)
				urls.append(url)
				urls.append(url + '&page50')


			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()
			threads = []
			append = threads.append
			for url in urls:
				append(workers.Thread(self.get_items, url))
			[i.start() for i in threads]
			[i.join() for i in threads]
			threads2 = []
			append2 = threads2.append
			self.items = [i for n, i in enumerate(self.items) if i[2] not in [x[2] for x in self.items[:n]]]
			for i in self.items:
				append2(workers.Thread(self.get_sources, i))
			[i.start() for i in threads2]
			[i.join() for i in threads2]
			return self.sources
		except:
			source_utils.scraper_error('YGGTORRENT')
			return self.sources


	def get_items(self, url):
		try:
			results = client.request(url, timeout='7')
			if not results or '<tbody' not in results: return
			parsed_results = client.parseDOM(results, 'tbody')
			if parsed_results is None or len(parsed_results) < 2: return
			table = parsed_results[1]
			rows = client.parseDOM(table, 'tr')
		except:
			source_utils.scraper_error('YGGTORRENT')
			return
		for row in rows:
			try:
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)
				link = client.parseDOM(columns[1], 'a', ret='href')[0]
				name = unquote_plus(client.parseDOM(columns[1], 'a')[0])
				name = source_utils.clean_name(name)
				if not source_utils.check_title(self.title, self.aliases, name, self.hdlr, self.year): continue
				name_info = source_utils.info_from_name(name, self.title, self.year, self.hdlr, self.episode_title)
				# if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				if not self.episode_title: #filter for eps returned in movie query (rare but movie and show exists for Run in 2020)
					ep_strings = [r'[.-]s\d{2}e\d{2}([.-]?)', r'[.-]s\d{2}([.-]?)', r'[.-]season[.-]?\d{1,2}[.-]?']
					name_lower = name.lower()
					if any(re.search(item, name_lower) for item in ep_strings): continue

				try:
					seeders = int(columns[7].replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				try:
					dsize, isize = source_utils._size(columns[5].replace('Go', 'gb'))
				except: isize = '0' ; dsize = 0
				self.items_append((name, name_info, link, isize, dsize, seeders))
			except:
				source_utils.scraper_error('YGGTORRENT')

	def get_sources(self, item):
		try:
			quality, info = source_utils.get_release_quality(item[1], item[2])
			if item[3] != '0': info.insert(0, item[3])
			info = ' | '.join(info)
			data = client.request(requote_uri(item[2]), timeout=7)
			hash = re.search(r'<td>([a-z0-9]{40})<\/td>', data, re.I).group(1)
			url = 'magnet:?xt=urn:btih:' + hash
			self.sources_append({'provider': 'yggtorrent', 'source': 'torrent', 'seeders': item[5], 'hash': hash, 'name': item[0], 'name_info': item[1],
													'quality': quality, 'language': 'fr', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': item[4]})
		except:
			source_utils.scraper_error('YGGTORRENT')

	def sources_packs(self, data, hostDict, search_series=False, total_seasons=None, bypass_filter=False):
		self.sources = []
		if not data: return self.sources
		self.sources_append = self.sources.append
		self.items = []
		self.items_append = self.items.append
		try:
			self.search_series = search_series
			self.total_seasons = total_seasons
			self.bypass_filter = bypass_filter

			self.title = data['tvshowtitle'].replace('&', 'and').replace('Special Victims Unit', 'SVU').replace('/', ' ').replace('$', 's')
			self.aliases = data['aliases']
			self.imdb = data['imdb']
			self.year = data['year']
			self.season_x = data['season']
			self.season_xx = self.season_x.zfill(2)
			self.undesirables = source_utils.get_undesirables()
			self.check_foreign_audio = source_utils.check_foreign_audio()

			queries = []
			search_terms = []

			if search_series:
				search_terms = ['Saison', 'Complete', 'Integrale']
			else:
				search_terms = ['S%s' % self.season_xx, 'Saison %s' % self.season_x]

			if data['aliases'] and data['aliases'][0]['country'] == 'fr':
				alias_title = data['aliases'][0]['title']
				queries.extend([self.search_link % self.get_query(alias_title + ' ' + term) for term in search_terms])

			queries.extend([self.search_link % self.get_query(self.title + ' ' + term) for term in search_terms])		
					
			threads = []
			append = threads.append
			for url in queries:
				link = '%s%s' % (self.base_link, url)
				append(workers.Thread(self.get_items2, link))
			[i.start() for i in threads]
			[i.join() for i in threads]
			threads2 = []
			append2 = threads2.append
			self.items = [i for n, i in enumerate(self.items) if i[2] not in [x[2] for x in self.items[:n]]]
			for i in self.items:
				append2(workers.Thread(self.get_sources_packs, i))
			[i.start() for i in threads2]
			[i.join() for i in threads2]
			return self.sources
		except:
			source_utils.scraper_error('YGGTORRENT')
			return self.sources

	def get_items2(self, url):
		try:
			results = client.request(url, timeout='7')
			if not results or '<tbody' not in results: return
			parsed_results = client.parseDOM(results, 'tbody')
			if parsed_results is None or len(parsed_results) < 2: return
			table = parsed_results[1]
			rows = client.parseDOM(table, 'tr')
		except:
			source_utils.scraper_error('YGGTORRENT')
			return
		for row in rows:
			try:
				columns = re.findall(r'<td.*?>(.+?)</td>', row, re.DOTALL)
				link = client.parseDOM(columns[1], 'a', ret='href')[0]
				name = unquote_plus(client.parseDOM(columns[1], 'a')[0])
				name = source_utils.clean_name(name)

				episode_start, episode_end = 0, 0
				package, last_season = None, None
				if not self.search_series:
					if not self.bypass_filter:
						valid, episode_start, episode_end = source_utils.filter_season_pack(self.title, self.aliases, self.year, self.season_x, name)
						if not valid: continue
					package = 'season'

				elif self.search_series:
					if not self.bypass_filter:
						valid, last_season = source_utils.filter_show_pack(self.title, self.aliases, self.imdb, self.year, self.season_x, name, self.total_seasons)
						if not valid: continue
					else: last_season = self.total_seasons
					package = 'show'
				
				name_info = source_utils.info_from_name(name, self.title, self.year, season=self.season_x, pack=package)
				# if source_utils.remove_lang(name_info, self.check_foreign_audio): continue
				if self.undesirables and source_utils.remove_undesirables(name_info, self.undesirables): continue

				try:
					seeders = int(columns[7].replace(',', ''))
					if self.min_seeders > seeders: continue
				except: seeders = 0

				try:
					dsize, isize = source_utils._size(columns[5].replace('Go', 'gb'))
				except: isize = '0' ; dsize = 0
				self.items_append((name, name_info, link, isize, dsize, seeders, package, last_season, episode_start, episode_end))
			except:
				source_utils.scraper_error('YGGTORRENT')
				return self.sources
			
	def get_sources_packs(self, item):
		try:
			quality, info = source_utils.get_release_quality(item[1], item[2])
			if item[3] != '0': info.insert(0, item[3])
			info = ' | '.join(info)
			data = client.request(requote_uri(item[2]), timeout='7')
			hash = re.search(r'<td>([a-z0-9]{40})<\/td>', data, re.I).group(1)
			url = 'magnet:?xt=urn:btih:' + hash

			item2 = {'provider': 'yggtorrent', 'source': 'torrent', 'seeders': item[5], 'hash': hash, 'name': item[0], 'name_info': item[1], 'quality': quality,
							'language': 'en', 'url': url, 'info': info, 'direct': False, 'debridonly': True, 'size': item[4], 'package': item[6]}
			if self.search_series: item2.update({'last_season': item[7]})
			elif item[8]: item2.update({'episode_start': item[8], 'episode_end': item[9]}) # for partial season packs
			self.sources_append(item2)
		except:
			source_utils.scraper_error('YGGTORRENT')

	def get_query(self, title, year=None):
		title = re.sub(r'([^\s]+)', r'"\1"', title.replace("\"", "").replace("-", " ").replace("/", " ").replace("!", "").replace("  ", "").strip())
		if year is None:
			return quote_plus(title)
		else:
			return quote_plus(title + ' "' + year + '"')