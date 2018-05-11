# python-metallum

A basic python API for the amazing www.metal-archives.com

## Install

`pip install python-metallum`

## Usage

Artist search

```python
import metallum


# Search bands matching term
bands = metallum.band_search('metallica')
# -> [<SearchResult: Metallica | Thrash Metal (early), Hard Rock/Heavy/Thrash Metal (later) | United States>]

bands[0].name
# -> 'Metallica'

# Fetch band page
band = bands[0].get()

# Get all albums
band.albums
# -> [<Album: No Life 'til Leather (Demo)>, <Album: Kill 'Em All (Full-length)>, ...]

# Get only full-length albums
full_length = band.albums.search(type=metallum.AlbumTypes.FULL_LENGTH)
# -> [<Album: Kill 'Em All (Full-length)>, <Album: Ride the Lightning (Full-length)>, <Album: Master of Puppets (Full-length)>, <Album: ...and Justice for All (Full-length)>, <Album: Metallica (Full-length)>, <Album: Load (Full-length)>, <Album: ReLoad (Full-length)>, <Album: Garage Inc. (Full-length)>, <Album: St. Anger (Full-length)>, <Album: Death Magnetic (Full-length)>, <Album: Hardwired... to Self-Destruct (Full-length)>]

album = full_length[2]
album.title
# -> 'Master of Puppets'

album.date
# -> datetime.datetime(1986, 3, 3, 0, 0)

# Get all tracks
album.tracks
# -> [<Track: Battery (313)>, <Track: Master of Puppets (516)>, <Track: The Thing That Should Not Be (397)>, <Track: Welcome Home (Sanitarium) (388)>, <Track: Disposable Heroes (497)>, <Track: Leper Messiah (341)>, <Track: Orion (508)>, <Track: Damage, Inc. (330)>]
```

Album search

```python
import metallum

# Search albums matching term
metallum.album_search('seventh')
# -> []

# Search albums containing term
metallum.album_search('seventh', strict=False)
# -> [<SearchResult: Beherit | Seventh Blasphemy | Demo>, <SearchResult: Black Sabbath | Seventh Star | Full-length>, ...]

# Search albums by band
metallum.album_search('seventh', band='iron maiden', strict=False)
# -> [<SearchResult: Iron Maiden | Seventh Son of a Seventh Son | Full-length>]

```

Refer to source and doctests for detailed usage

