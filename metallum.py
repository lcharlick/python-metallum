#!/usr/bin/env python
# encoding: utf-8

"""Python interface for www.metal-archives.com
"""
import datetime
import json
import re
import time
import os.path
import tempfile
from typing import List, Optional
from urllib.parse import urlencode

import requests_cache
from dateutil import parser as date_parser
from pyquery import PyQuery
from requests_cache.core import remove_expired_responses

CACHE_FILE = os.path.join(tempfile.gettempdir(), 'metallum_cache')
requests_cache.install_cache(cache_name=CACHE_FILE, expire_after=300)
remove_expired_responses()

# Site details
BASE_URL = 'https://www.metal-archives.com'
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2227.1 Safari/537.36'
ENC = 'utf8'

# HTML entities
BR = '<br/>'
CR = '&#13;'

# Timeout between page requests, in seconds
REQUEST_TIMEOUT = 1.0

# UTC offset
UTC_OFFSET = 4


class NetworkError(Exception):
    """Exception conveying a problem in sending a request"""


def map_params(params, m):
    res = {}
    for k, v in params.items():
        if v is not None:
            res[m.get(k, k)] = v
    return res


def band_for_id(id: str) -> 'Band':
    return Band('bands/_/{0}'.format(id))


def band_search(name, strict=True, genre=None, countries=[], year_created_from=None,
                year_created_to=None, status=[], themes=None, location=None, label=None,
                page_start=0) -> 'Search':
    """Perform an advanced band search.
    """
    # Create a dict from the method arguments
    params = locals()

    # Convert boolean value to integer
    params['strict'] = str(int(params['strict']))

    # Map method arguments to their url query string counterparts
    params = map_params(params, {
        'name': 'bandName',
        'strict': 'exactBandMatch',
        'countries': 'country[]',
        'year_created_from': 'yearCreationFrom',
        'year_created_to': 'yearCreationTo',
        'status': 'status[]',
        'label': 'bandLabelName',
        'page_start': 'iDisplayStart'
    })

    # Build the search URL
    url = 'search/ajax-advanced/searching/bands/?' + urlencode(params, True)

    return Search(url, BandResult)


def album_for_id(id: str) -> 'AlbumWrapper':
    return AlbumWrapper(url='albums/_/_/{0}'.format(id))


def album_search(title, strict=True, band=None, band_strict=True, year_from=None,
                 year_to=None, month_from=None, month_to=None, countries=[], location=None, label=None,
                 indie_label=False, genre=None, types=[], page_start=0) -> 'Search':
    """Perform an advanced album search
    """
    # Create a dict from the method arguments
    params = locals()

    # Convert boolean value to integer
    params['strict'] = str(int(params['strict']))
    params['band_strict'] = str(int(params['band_strict']))
    params['indie_label'] = str(int(params['indie_label']))

    # Month values must be present if year is supplied
    if year_from and not month_from:
        params['month_from'] = '1'
    if year_to and not month_to:
        params['month_to'] = '12'

    # Map method arguments to their url query string counterparts
    params = map_params(params, {
        'title': 'releaseTitle',
        'strict': 'exactReleaseMatch',
        'band': 'bandName',
        'band_strict': 'exactBandMatch',
        'year_from': 'releaseYearFrom',
        'year_to': 'releaseYearTo',
        'month_from': 'releaseMonthFrom',
        'month_to': 'releaseMonthTo',
        'countries': 'country[]',
        'label': 'releaseLabelName',
        'indie_label': 'indieLabel',
        'types': 'releaseType[]',
        'page_start': 'iDisplayStart'
    })

    # Build the search URL
    url = 'search/ajax-advanced/searching/albums/?' + urlencode(params, True)

    return Search(url, AlbumResult)


def lyrics_for_id(id: int) -> 'Lyrics':
    return Lyrics(id)


class AlbumTypes(object):
    """Enum of all possible album types
    """
    FULL_LENGTH = 'Full-length'
    EP = 'EP'
    SINGLE = 'Single'
    DEMO = 'Demo'
    VIDEO = 'Video/VHS'
    COMPILATION = 'Compilation'
    DVD = 'DVD'
    LIVE = 'Live album'
    SPLIT = 'Split'


def make_absolute(endpoint: str) -> str:
    """Make relative URLs absolute
    """
    return '{0}/{1}'.format(BASE_URL, endpoint)


def offset_time(t: datetime.datetime) -> datetime.datetime:
    """Convert server time to UTC
    """
    td = datetime.timedelta(hours=UTC_OFFSET)
    return t + td


class Metallum(object):
    """Base metallum class - represents a metallum page
    """
    _last_request = None

    def __init__(self, url):
        self._session = requests_cache.CachedSession(cache_name=CACHE_FILE)
        self._session.hooks = {'response': self._make_throttle_hook()}
        self._session.headers = {'User-Agent': USER_AGENT}

        self._html = self._fetch_page(url)
        self._page = PyQuery(self._html)

    def _make_throttle_hook(self):
        """
        Returns a response hook function which sleeps for `timeout` seconds if
        response is not cached
        """
        def hook(response, *args, **kwargs):
            is_cached = getattr(response, 'from_cache', False)
            if not is_cached:
                time.sleep(REQUEST_TIMEOUT)
            # print("{}{}".format(response.request.url, " (CACHED)" if is_cached else ""))
            return response
        return hook

    def _fetch_page(self, url) -> bytes:
        res = self._session.get(make_absolute(url))
        return res.content


class MetallumEntity(Metallum):
    """Represents a metallum entity (artist, album...)
    """
    def _dd_element_for_label(self, label: str) -> Optional[PyQuery]:
        """Data on entity pages are stored in <dt> / <dd> pairs
        """
        labels = list(self._page('dt').contents())

        try:
            index = labels.index(label)
        except ValueError:
            return None

        return self._page('dd').eq(index)

    def _dd_text_for_label(self, label: str) -> str:
        element = self._dd_element_for_label(label)
        return element.text() if element else ""


class MetallumCollection(Metallum, list):
    """Base metallum class for collections (e.g. albums)
    """
    def __init__(self, url):
        super().__init__(url)

    def search(self, **kwargs) -> 'MetallumCollection':
        """Query the collection based on one or more key value pairs, where the
        keys are attributes of the contained objects:

        >>> len(b.albums.search(title='master of puppets'))
        2

        >>> len(b.albums.search(title='master of puppets', type=AlbumTypes.FULL_LENGTH))
        1
        """
        collection = self[:]
        for arg in kwargs:
            for item in collection[:]:
                if kwargs[arg].lower() != getattr(item, arg).lower():
                    try:
                        collection.remove(item)
                    except ValueError:
                        continue
        return collection


class Search(Metallum, list):

    def __init__(self, url, result_handler):
        super().__init__(url)

        data = json.loads(self._html)
        results = data['aaData']
        for result in results:
            self.append(result_handler(result))

        self.result_count = int(data['iTotalRecords'])


class SearchResult(list):
    """Represents a search result in an advanced search
    """
    _resultType = None

    def __init__(self, details):
        super().__init__()
        for detail in details:
            if re.match('^<a href.*', detail):
                d = PyQuery(detail)
                self.append(d('a').text())
            else:
                self.append(detail)

    def __repr__(self):
        s = ' | '.join(self)
        return '<SearchResult: {0}>'.format(s)

    def get(self) -> 'Metallum':
        return self._resultType(self.url)


class BandResult(SearchResult):

    def __init__(self, details):
        super().__init__(details)
        self._details = details
        self._resultType = Band

    @property
    def id(self) -> str:
        """
        >>> s[0].id
        '125'
        """
        url = PyQuery(self._details[0])('a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def url(self) -> str:
        return 'bands/_/{0}'.format(self.id)

    @property
    def name(self) -> str:
        """
        >>> s[0].name
        'Metallica'
        """
        return self[0]

    @property
    def genres(self) -> List[str]:
        """
        >>> s[0].genres
        ['Thrash Metal (early)', 'Hard Rock/Heavy/Thrash Metal (later)']
        """
        return self[1].split(', ')

    @property
    def country(self) -> str:
        """
        >>> s[0].country
        'United States'
        """
        return self[2]


class AlbumResult(SearchResult):

    def __init__(self, details):
        super().__init__(details)
        self._details = details
        self._resultType = AlbumWrapper

    @property
    def id(self) -> str:
        url = PyQuery(self._details[1])('a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def url(self) -> str:
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def title(self) -> str:
        return self[1]

    @property
    def type(self) -> str:
        return self[2]

    @property
    def bands(self) -> List['Band']:
        bands = []
        el = PyQuery(self._details[0]).wrap('<div></div>')
        for a in el.find('a'):
            url = PyQuery(a).attr('href')
            id = re.search('\d+$', url).group(0)
            bands.append(Band('bands/_/{0}'.format(id)))
        return bands

    @property
    def band_name(self) -> str:
        return self[0]


class Band(MetallumEntity):

    def __init__(self, url):
        super().__init__(url)

    def __repr__(self):
        return '<Band: {0}>'.format(self.name)

    @property
    def id(self) -> str:
        """
        >>> b.id
        '125'
        """
        url = self._page('.band_name a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def url(self) -> str:
        return 'bands/_/{0}'.format(self.id)

    @property
    def added(self) -> Optional[datetime.datetime]:
        """
        >>> type(b.added)
        <class 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(0).text()[10:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def modified(self) -> Optional[datetime.datetime]:
        """
        >>> type(b.modified)
        <class 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(1).text()[18:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def name(self) -> str:
        """
        >>> b.name
        'Metallica'
        """
        return self._page('h1.band_name').text().strip()

    @property
    def country(self) -> str:
        """
        >>> b.country
        'United States'
        """
        return self._dd_text_for_label('Country of origin:')

    @property
    def location(self) -> str:
        """
        >>> b.location
        'Los Angeles/San Francisco, California'
        """
        return self._dd_text_for_label('Location:')

    @property
    def status(self) -> str:
        """
        >>> b.status
        'Active'
        """
        return self._dd_text_for_label('Status:')

    @property
    def formed_in(self) -> str:
        """
        >>> b.formed_in
        '1981'
        """
        return self._dd_text_for_label('Formed in:')

    @property
    def genres(self) -> List[str]:
        """
        >>> b.genres
        ['Thrash Metal (early)', 'Hard Rock/Heavy/Thrash Metal (later)']
        """
        return self._dd_text_for_label('Genre:').split(', ')

    @property
    def themes(self) -> List[str]:
        """
        >>> b.themes
        ['Corruption', 'Death', 'Life', 'Internal struggles', 'Anger']
        """
        return self._dd_text_for_label('Lyrical themes:').split(', ')

    @property
    def label(self) -> str:
        """
        >>> b.label
        'Blackened Recordings'
        """
        return self._dd_text_for_label('Current label:')

    @property
    def logo(self) -> str:
        """
        >>> b.logo
        'https://www.metal-archives.com/images/1/2/5/125_logo.png'
        """
        url = self._page('#logo').attr('href')
        return url[:url.find('?')]

    @property
    def photo(self) -> str:
        """
        >>> b.photo
        'https://www.metal-archives.com/images/1/2/5/125_photo.jpg'
        """
        url = self._page('#photo').attr('href')
        return url[:url.find('?')]

    @property
    def albums(self) -> List['AlbumCollection']:
        """
        >>> len(b.albums) > 0
        True

        >>> type(b.albums[0])
        <class '__main__.AlbumWrapper'>
        """
        url = 'band/discography/id/{0}/tab/all'.format(self.id)
        return AlbumCollection(url)


class AlbumCollection(MetallumCollection):

    def __init__(self, url):
        super().__init__(url)

        rows = self._page('tr:gt(0)')
        for index, album in enumerate(rows):
            self.append(AlbumWrapper(elem=rows.eq(index)))


class AlbumWrapper(Metallum):
    """Wrapper class for Album / LazyAlbum

    Album instances are created automatically when an attribute is accessed that
    is not provided by LazyAlbum:

    >>> a = b.albums[1]
    >>> a.label
    'Megaforce Records'

    The above causes an Album instance to be created (requires an extra page request!):

    >>> type(a._album)
    <class '__main__.Album'>
    """

    def __init__(self, url=None, elem=None):
        if url:
            super().__init__(url)
            self._album = Album(url)
        elif elem:
            self._album = LazyAlbum(elem)

    def __repr__(self):
        return '<Album: {0} ({1})>'.format(self.title, self.type)

    def __getattr__(self, name):
        if not hasattr(self._album, name) and hasattr(Album, name):
            self._album = Album(self._album.url)
        return getattr(self._album, name)

    @property
    def tracks(self):
        """
        >>> len(a.tracks)
        8
        """
        return TrackCollection(self._album.url, self)

    @property
    def disc_count(self):
        """
        >>> a.disc_count
        1

        >>> a3.disc_count
        2
        """
        discs = 0
        for track in self.tracks:
            if track.disc_number > discs:
                discs = track.disc_number
        return discs


class Album(MetallumEntity):

    def __init__(self, url):
        super().__init__(url)

    @property
    def id(self) -> str:
        """
        >>> a.id
        '547'
        """
        url = self._page('.album_name a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def url(self) -> str:
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def bands(self) -> List[Band]:
        """Return a list of band objects. The list will only contain
        multiple bands when the album is of type 'Split'.

        >>> a.bands
        [<Band: Metallica>]

        >>> a2.bands
        [<Band: Lunar Aurora>, <Band: Paysage d'Hiver>]
        """
        bands = []
        for a in self._page('.band_name').find('a'):
            url = PyQuery(a).attr('href')
            id = re.search('\d+$', url).group(0)
            bands.append(Band('bands/_/{0}'.format(id)))
        return bands

    @property
    def added(self) -> Optional[datetime.datetime]:
        """
        >>> type(a.added)
        <class 'NoneType'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(0).text()[10:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def modified(self) -> Optional[datetime.datetime]:
        """
        >>> type(a.modified)
        <class 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(1).text()[18:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def title(self) -> str:
        """
        >>> a.title
        'Master of Puppets'
        """
        return self._page('h1.album_name a').text()

    @property
    def type(self) -> str:
        """
        >>> a.type
        'Full-length'
        """
        element = self._dd_element_for_label('Type:')
        return element.text() if element else ""

    @property
    def date(self) -> Optional[datetime.datetime]:
        """
        >>> a.date
        datetime.datetime(1986, 3, 3, 0, 0)
        """
        s = self._dd_text_for_label('Release date:')

        # Date has no day portion
        if len(s) > 4 and ',' not in s:
            date = datetime.datetime.strptime(s, '%B %Y')
        else:
            date = date_parser.parse(s)
        return date

    @property
    def year(self) -> int:
        """
        >>> a.year
        1986
        """
        return int(self.date.year)

    @property
    def label(self) -> str:
        """
        >>> a.label
        'Elektra Records'

        >>> a3.label
        'Osmose Productions'
        """
        element = self._dd_element_for_label('Label:')
        return element('a').text() if element else ""

    @property
    def score(self) -> Optional[int]:
        """
        >>> a.score
        78

        >>> a2.score
        94

        >>> a3.score
        97
        """
        element = self._dd_element_for_label('Reviews:')
        if not element:
            return None

        score = re.search('(\d{1,3})%', element.text())
        if not score:
            return None

        return int(score.group(1))

    @property
    def cover(self) -> str:
        """
        >>> a.cover
        'https://www.metal-archives.com/images/5/4/7/547.jpg'
        """
        url = self._page('#cover').attr('href')
        return url[:url.find('?')]


class LazyAlbum:

    def __init__(self, elem):
        self._elem = elem

    @property
    def id(self) -> str:
        """
        >>> a.id
        '547'
        """
        url = self._elem('td').eq(0)('a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def url(self) -> str:
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def title(self) -> str:
        """
        >>> a.title
        'Master of Puppets'
        """
        return self._elem('td').eq(0)('a').text()

    @property
    def type(self) -> str:
        """
        >>> a.type
        'Full-length'
        """
        return self._elem('td').eq(1).text()

    @property
    def year(self) -> int:
        """
        >>> a.year
        1986
        """
        return int(self._elem('td').eq(2).text())


class TrackCollection(MetallumCollection):

    def __init__(self, url, album):
        super().__init__(url)

        disc = 1
        overall_number = 1
        rows = self._page('table.table_lyrics').find('tr.odd, tr.even').not_('.displayNone')
        for index, track in enumerate(rows):
            track = Track(rows.eq(index), album, disc, overall_number)
            if index != 0 and track.number == 1:
                disc += 1
                track._disc_number = disc
            overall_number += 1
            self.append(track)


class Track(object):

    def __init__(self, elem, album, disc_number, overall_number):
        self._elem = elem
        self.album = album
        self._disc_number = disc_number
        self._overall_number = overall_number

    def __repr__(self):
        return '<Track: {0} ({1})>'.format(self.title, self.duration)

    @property
    def id(self) -> str:
        """
        >>> t.id
        '5018A'
        """
        return self._elem('td').eq(0)('a').attr('name')

    @property
    def number(self) -> int:
        """
        >>> t.number
        1

        >>> a3.tracks[0].number
        1

        >>> a3.tracks[-1].number
        4
        """
        return int(self._elem('td').eq(0).text()[:-1])

    @property
    def overall_number(self) -> int:
        """
        >>> t.overall_number
        1

        >>> a3.tracks[0].overall_number
        1

        >>> a3.tracks[-1].overall_number
        8
        """
        return self._overall_number

    @property
    def disc_number(self) -> int:
        """
        >>> t.disc_number
        1

        >>> a3.tracks[0].disc_number
        1

        >>> a3.tracks[-1].disc_number
        2
        """
        return self._disc_number

    @property
    def full_title(self) -> str:
        """
        >>> t.full_title
        'Battery'

        >>> t2.full_title
        'Lunar Aurora - A haudiga Fluag'
        """
        return self._elem('td').eq(1).text().replace('\n', '').replace('\t', '')

    @property
    def title(self) -> str:
        """
        >>> t.title
        'Battery'

        >>> t2.title
        'A haudiga Fluag'
        """
        title = self.full_title
        # Remove band name from split album track titles
        if self.album.type == AlbumTypes.SPLIT:
            title = title[len(self.band.name) + 3:]
        return title

    @property
    def duration(self) -> int:
        """
        >>> t.duration
        313
        """
        s = self._elem('td').eq(2).text()
        if s:
            parts = s.split(':')
            seconds = int(parts[-1])
            if len(parts) > 1:
                seconds += int(parts[-2]) * 60
            if len(parts) == 3:
                seconds += int(parts[0]) * 3600
        else:
            seconds = 0
        return seconds

    @property
    def band(self) -> Band:
        """
        >>> t.band
        <Band: Metallica>

        >>> t2.band
        <Band: Lunar Aurora>
        """
        if self.album.type == AlbumTypes.SPLIT:
            for band in self.album.bands:
                if self.full_title.startswith(band.name):
                    break
        else:
            band = self.album.bands[0]
        return band

    @property
    def lyrics(self) -> 'Lyrics':
        """
        >>> str(t.lyrics).split('\\n')[0]
        'Lashing out the action, returning the reaction'
        """
        return Lyrics(self.id)


class Lyrics(Metallum):

    def __init__(self, id):
        super().__init__('release/ajax-view-lyrics/id/{0}'.format(id))

    def __str__(self):
        lyrics = self._page('p').html()
        if not lyrics:
            return ''
        return lyrics.replace(BR * 2, '\n').replace(BR, '').replace(CR, '').strip()


if __name__ == '__main__':
    import doctest

    # Test objects
    s = band_search('metallica')
    b = s[0].get()
    a = b.albums.search(type=AlbumTypes.FULL_LENGTH)[2]
    t = a.tracks[0]

    # Objects for split album tests
    a2 = album_for_id('42682')
    t2 = a2.tracks[2]

    # Objects for multi-disc album testing
    a3 = album_for_id('338756')

    doctest.testmod(globs=locals())
