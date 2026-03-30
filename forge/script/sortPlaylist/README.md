# sortPlaylist

Sorts an extended M3U playlist newest-first by extracting the first `YYYY-MM-DD`
date from each track URL.

Default standalone usage from this directory:

```bash
./reorder_playlist.m3u.sh
```

That reads `playlist.m3u` and writes `playlist.sorted.m3u`.

In-place usage:

```bash
./reorder_playlist.m3u.sh --in-place /path/to/playlist.m3u
```

`../stagePublisher.sh` uses the in-place form against `$STAGE/sotd/playlist.m3u`
after staging the SOTD build and before the rest of publish processing.
