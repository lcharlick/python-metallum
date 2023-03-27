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

Song search

```python
import metallum

# Search songs matching term
metallum.song_search('fear of the')
# -> []

# Search songs containing term
metallum.album_search('fear of the', strict=False)
# -> [<SearchResult: Antipope | 3 Eyes of Time | Full-length | The Fear of Fear | Progressive Black Metal (early); Progressive/Gothic/Industrial Metal (later) | 2588300>, ...]

# Search songs by band
metallum.song_search('fear of the', band='iron maiden', strict=False)
# -> [<SearchResult: Iron Maiden | A Real Live One | Live album | Fear of the Dark | Heavy Metal, NWOBHM | 501324>, ...]

# Search songs by release
metallum.song_search('fear of the', release='fear of the dark', strict=False)
# -> [<SearchResult: Iron Maiden | Fear of the Dark | Full-length | Fear of the Dark | Heavy Metal, NWOBHM | 3449>, ...]

```

Refer to source and doctests for detailed usage

