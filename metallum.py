#!/usr/bin/env python
# encoding: utf-8

"""Python interface for www.metal-archives.com
"""
import re
import json
import time
import random
import datetime

from pyquery import PyQuery
from urllib import quote
from urllib2 import urlopen


# Site details
BASE_URL = 'http://www.metal-archives.com'
ENC = 'utf8'

# HTML entities
BR = '<br/>'
CR = '&#13;'

# Cache expiry time, in seconds
CACHE_EXPIRY = 600

# Min / max timeout between page requests, in seconds
REQUEST_TIMEOUT = (3, 7)

# UTC offset
UTC_OFFSET = 4


def band_by_id(id):
    return Band('bands/_/{0}'.format(id))


def band_search(name):
    url = u'search/ajax-advanced/searching/bands/?bandName={0}&exactBandMatch=1'.format(quote(name.encode(ENC)))
    return Search(url, BandResult)


def album_by_id(id):
    return AlbumWrapper(url='albums/_/_/{0}'.format(id))


def album_search(title):
    url = u'search/ajax-advanced/searching/albums/?releaseTitle={0}&exactReleaseMatch=1'.format(quote(title.encode(ENC)))
    return Search(url, AlbumResult)


class NoSearchResultsError(Exception):
    """ Search returned no results """


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


def make_absolute(endpoint):
    """Make relative URLs absolute
    """
    return u'{0}/{1}'.format(BASE_URL, endpoint)


def offset_time(t):
    """Convert server time to UTC
    """
    td = datetime.timedelta(hours=UTC_OFFSET)
    return t + td


class cache(object):
    def __init__(self, expiry=0):
        self.store = {}
        self.expiry = expiry

    def __call__(self, func):
        def _cache(obj, url):
            if url in self.store:
                t, result = self.store[url]
                if self.expiry and (time.time() - t) < self.expiry:
                    return self.store[url][1]
            result = func(obj, url)
            self.store[url] = (time.time(), result)
            return result
        return _cache


class Metallum(object):
    """Base metallum class - represents a metallum page
    """
    _last_request = None

    def __init__(self, url):
        self._html = self._fetch_page(url)
        self._page = PyQuery(self._html)

    @cache(CACHE_EXPIRY)
    def _fetch_page(self, url):
        if Metallum._last_request:
            time_since_request = time.time() - Metallum._last_request
            timeout = random.uniform(*REQUEST_TIMEOUT)
            if time_since_request < timeout:
                time.sleep(timeout - time_since_request)
        Metallum._last_request = time.time()
        return urlopen(make_absolute(url)).read().decode(ENC)


class MetallumCollection(Metallum, list):
    """Base metallum class for collections (e.g. albums)
    """
    def __init__(self, url):
        super(MetallumCollection, self).__init__(url)

    def search(self, **kwargs):
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
                if unicode(kwargs[arg]).lower() != unicode(getattr(item, arg)).lower():
                    try:
                        collection.remove(item)
                    except ValueError:
                        continue
        return collection


class Search(Metallum, list):

    def __init__(self, url, result_handler):
        super(Search, self).__init__(url)

        results = json.loads(self._html)['aaData']
        if not len(results):
            raise NoSearchResultsError
        else:
            for result in results:
                self.append(result_handler(result))

    def __getitem__(self, index):
        return list.__getitem__(self, index).transform()


class SearchResult(list):
    """Represents a search result in an advanced search
    """
    def __init__(self, details):
        for detail in details:
            if re.match('^<a href.*', detail):
                d = PyQuery(detail)
                self.append(d('a').text())
            else:
                self.append(detail)

    def __repr__(self):
        s = ' | '.join(self).encode(ENC)
        return '<SearchResult: {0}>'.format(s)

    def transform(self):
        return self._type(self.url)


class BandResult(SearchResult):

    def __init__(self, details):
        super(BandResult, self).__init__(details)
        self._details = details
        self._type = Band

    @property
    def id(self):
        url = PyQuery(self._details[0])('a').attr('href')
        return int(re.search('\d+$', url).group(0))

    @property
    def url(self):
        return 'bands/_/{0}'.format(self.id)

    @property
    def name(self):
        return self[0]

    @property
    def genres(self):
        return self[1].split(', ')

    @property
    def country(self):
        return self[2]


class AlbumResult(SearchResult):

    def __init__(self, details):
        super(AlbumResult, self).__init__(details)
        self._details = details
        self._type = AlbumWrapper

    @property
    def id(self):
        url = PyQuery(self._details[1])('a').attr('href')
        return int(re.search('\d+$', url).group(0))

    @property
    def url(self):
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def title(self):
        return self[1]

    @property
    def type(self):
        return self[2]

    @property
    def band_id(self):
        url = PyQuery(self._details[0])('a').attr('href')
        return re.search('\d+$', url).group(0)

    @property
    def band_url(self):
        return 'bands/_/{0}'.format(self.band_id)

    @property
    def band(self):
        return Band(self.band_url)

    @property
    def band_name(self):
        return self[0]


class Band(Metallum):

    def __init__(self, url):
        super(Band, self).__init__(url)

    def __repr__(self):
        return '<Band: {0}>'.format(self.name.encode(ENC))

    @property
    def id(self):
        """
        >>> b.id
        125
        """
        url = self._page('.band_name a').attr('href')
        return int(re.search('\d+$', url).group(0))

    @property
    def url(self):
        return 'bands/_/{0}'.format(self.id)

    @property
    def added(self):
        """
        >>> type(b.added)
        <type 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(0).text()[10:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def modified(self):
        """
        >>> type(b.modified)
        <type 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(1).text()[18:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def name(self):
        """
        >>> b.name
        'Metallica'
        """
        return self._page('h1.band_name').text().strip()

    @property
    def country(self):
        """
        >>> b.country
        'United States'
        """
        return self._page('dd').eq(0)('a').text()

    @property
    def location(self):
        """
        >>> b.location
        'Los Angeles/San Francisco, California'
        """
        return self._page('dd').eq(1).text()

    @property
    def status(self):
        """
        >>> b.status
        'Active'
        """
        return self._page('dd').eq(2).text()

    @property
    def formed_in(self):
        """
        >>> b.formed_in
        1981
        """
        return int(self._page('dd').eq(3).text())

    @property
    def genres(self):
        """
        >>> b.genres
        ['Thrash Metal', 'Modern Rock/Metal']
        """
        return self._page('dd').eq(4).text().split(', ')

    @property
    def themes(self):
        """
        >>> b.themes
        ['Corruption', 'Death', 'Life', 'Internal Struggles', 'Anger']
        """
        return self._page('dd').eq(5).text().split(', ')

    @property
    def label(self):
        """
        >>> b.label
        'Blackened Recordings'
        """
        elem = self._page('dd').eq(6)
        if elem('a'):
            elem = elem('a')
        return elem.text()

    @property
    def logo(self):
        """
        >>> b.logo
        'http://www.metal-archives.com/images/1/2/5/125_logo.png?4830'
        """
        return self._page('#logo').attr('href')

    @property
    def photo(self):
        """
        >>> b.photo
        'http://www.metal-archives.com/images/1/2/5/125_photo.jpg?4206'
        """
        return self._page('#photo').attr('href')

    @property
    def albums(self):
        """
        >>> len(b.albums) > 100
        True
        """
        url = 'band/discography/id/{0}/tab/all'.format(self.id)
        return Albums(url)


class Albums(MetallumCollection):

    def __init__(self, url):
        super(Albums, self).__init__(url)

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
            self._album = Album(url)
        elif elem:
            self._album = LazyAlbum(elem)

    def __repr__(self):
        return '<Album: {0} ({1})>'.format(self.title.encode(ENC), self.type)

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
        return Tracks(self._album.url)


class Album(Metallum):

    def __init__(self, url):
        super(Album, self).__init__(url)

    @property
    def id(self):
        """
        >>> a.id
        547
        """
        url = self._page('.album_name a').attr('href')
        return int(re.search('\d+$', url).group(0))

    @property
    def url(self):
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def band(self):
        url = self._page('.band_name a').attr('href')
        id = re.search('\d+$', url).group(0)
        return Band('bands/_/{0}'.format(id))

    @property
    def added(self):
        """
        >>> type(a.added)
        <type 'NoneType'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(0).text()[10:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def modified(self):
        """
        >>> type(a.modified)
        <type 'datetime.datetime'>
        """
        s = self._page('#auditTrail').find('tr').eq(1).find('td').eq(1).text()[18:]
        try:
            return offset_time(datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S'))
        except ValueError:
            return None

    @property
    def title(self):
        """
        >>> a.title
        'Master of Puppets'
        """
        return self._page('h1.album_name a').text()

    @property
    def type(self):
        """
        >>> a.type
        'Full-length'
        """
        return self._page('dd').eq(0).text()

    @property
    def date(self):
        """
        >>> a.date
        datetime.datetime(1986, 2, 21, 0, 0)
        """
        try:
            from dateutil import parser
        except ImportError:
            return None

        s = self._page('dd').eq(1).text()

        # Date has no day portion
        if len(s) > 4 and ',' not in s:
            date = datetime.datetime.strptime(s, '%B %Y')
        else:
            date = parser.parse(s)
        return date

    @property
    def year(self):
        """
        >>> a.year
        1986
        """
        return int(self._page('dd').eq(1).text()[-4:])

    @property
    def label(self):
        """
        >>> a.label
        'Elektra'
        """
        return self._page('dd').eq(2)('a').text()

    @property
    def score(self):
        """
        >>> a.score
        79
        """
        score = re.search('(\d{1,2})%', self._page('dd').eq(3).text())
        if score:
            return int(score.group(1))
        return None

    @property
    def cover(self):
        """
        >>> a.cover
        'http://www.metal-archives.com/images/5/4/7/547.jpg?4520'
        """
        return self._page('#cover').attr('href')


class LazyAlbum:

    def __init__(self, elem):
        self._elem = elem

    @property
    def id(self):
        """
        >>> a.id
        547
        """
        url = self._elem('td').eq(0)('a').attr('href')
        return int(re.search('\d+$', url).group(0))

    @property
    def url(self):
        return 'albums/_/_/{0}'.format(self.id)

    @property
    def title(self):
        """
        >>> a.title
        'Master of Puppets'
        """
        return self._elem('td').eq(0)('a').text()

    @property
    def type(self):
        """
        >>> a.type
        'Full-length'
        """
        return self._elem('td').eq(1).text()

    @property
    def year(self):
        """
        >>> a.year
        1986
        """
        return int(self._elem('td').eq(2).text())


class Tracks(MetallumCollection):

    def __init__(self, url):
        super(Tracks, self).__init__(url)

        rows = self._page('table.table_lyrics').find('tr.odd, tr.even').not_('.displayNone')
        for index, track in enumerate(rows):
            self.append(Track(rows.eq(index)))

        # Set disc numbers
        disc = 0
        for track in self:
            if track.number == 1:
                disc += 1
            track.disc = disc


class Track:

    def __init__(self, elem):
        self._elem = elem

    def __repr__(self):
        return '<Track: {0} ({1})>'.format(self.title.encode(ENC), self.duration)

    @property
    def id(self):
        """
        >>> t.id
        5018
        """
        return int(self._elem('td').eq(0)('a').attr('name'))

    @property
    def number(self):
        """
        >>> t.number
        1
        """
        return int(self._elem('td').eq(0).text()[:-1])

    @property
    def title(self):
        """
        >>> t.title
        'Battery'
        """
        return self._elem('td').eq(1).text().strip()

    @property
    def duration(self):
        """
        >>> t.duration
        312
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
    def lyrics(self):
        """
        >>> t.lyrics.split('\\n')[0]
        u'Lashing out the action, returning the reaction'
        """
        return unicode(Lyrics(self.id))


class Lyrics(Metallum):

    def __init__(self, id):
        super(Lyrics, self).__init__('release/ajax-view-lyrics/id/{0}'.format(id))

    def __unicode__(self):
        lyrics = self._page('p').html()
        if not lyrics:
            return ''
        return lyrics.replace(BR * 2, '\n').replace(BR, '').replace(CR, '').strip()


if __name__ == '__main__':
    import doctest

    b = band_search('metallica')[0]
    a = b.albums.search(type='Full-length')[2]
    t = a.tracks[0]
    doctest.testmod(globs=locals())
