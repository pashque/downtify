---
icon: lucide/library
---

# Library catalog & path sync

Downtify keeps a small **catalog** of the files under `/downloads` (the slskd folder, when [slskd files are left in place](slskd-navidrome.md#leave-files-in-place), and [extra folders](external-library.md) you add in Settings) so the Library page, player, M3U export, Navidrome sync and duplicate detection stay consistent when files move or playlists grow.

## What gets stored

| Store | Location | Purpose |
|-------|----------|---------|
| **Track index** | `/data/downtify_library.db` | Maps Spotify track IDs to library paths, so a track already on disk can be recognized |
| **Playlist catalog** | `/data/downtify_library.db` | Which tracks belong to each downloaded Spotify playlist |
| **Playlist downloads** | `/data/downtify_library.db` | Tracked Spotify playlist downloads and a cache of their Spotify track lists |
| **Navidrome index** | `/data/downtify_library.db` | Navidrome song IDs per file |
| **Library metadata cache** | `/data/downtify_library.db` | Title, artist, album, album artist, track number, year, length and cover size per file for `GET /tracks`, re-read only when a file's modification time or size changes |
| **Upgrade runs** | `/data/downtify_library.db` | The [library upgrade](library-upgrade.md) queue and when each track was last checked, so a run survives a restart |
| **Path scan cache** | RAM, plus a snapshot in `/data/downtify_library.db` | Folded `GET /tracks` rows, playlist listings and path pairs. UI routes serve this snapshot without walking the disk. Each finished download is **merged into the snapshot immediately** (so a new artist shows up without waiting). A delete **drops those files from the snapshot immediately** (so an album disappears from the grid without waiting). A full tree walk runs in the background a few seconds after the download queue is idle — not on a fixed timer. `GET /list?refresh=true` drops the snapshot and rescans now. |
| **Hidden items** | `/data/downtify_library.db` | The songs, albums and artists an admin [hid from users](users.md#hiding-from-users) |
| **Cover art cache** | `/data/cover_cache` (optional) | Extracted cover images for `GET /cover` |

Files are matched across moves by a **content key** — a hash of the file's name and size. Moving a file to another folder keeps its key; replacing it with a different file gives it a new one.

## Settings → Library

### Cache cover art on disk

When enabled, Downtify keeps extracted cover images under `/data/cover_cache`, so the Library and player don't re-read tags for every thumbnail. Safe to turn off anytime; it only costs disk space.

### Fix library paths

Use this after you **move or rename files on disk** outside Downtify, or delete them by hand.

1. Open **Settings → Library → Fix library paths**.
2. Downtify scans the library folders and:
    - **updates paths** in the track index and playlist catalog when a file is no longer where it was but the same file (same content key) is found elsewhere;
    - **removes stale entries** for files that no longer exist;
    - **indexes** older entries that were stored before content keys existed;
    - **follows [liked songs](liked-songs.md#keeping-likes-in-step-with-the-files)** to their new location.
3. If **Generate M3U** and/or **Create playlists in Navidrome** are enabled, the affected playlists are rewritten.

It only runs when you press the button (or call `POST /api/library/reconcile`) — never on a schedule.

### Existing music folders

To play a collection that Downtify did not download, add the folders in **Settings → Library** and press **Sync folders**. Files stay on disk; tags are read and artists are matched. See [Existing music folders](external-library.md).

::: warning
Rewriting a playlist deletes library files whose tags clearly don't match the Spotify track they're registered for — see [slskd & Navidrome](slskd-navidrome.md#playlist-sync).
:::

::: info Deletes vs moves
Deleting tracks from the **Library** page already cleans up the catalog and rewrites the affected M3U files and Navidrome playlists in the background, so there's nothing to fix afterwards.
:::

## Artist names and credits

Library and Link album headers hide the download action until destination checks finish, and keep it hidden once every canonical album-folder target is present, including singles and EPs. Missing/partial actions are never rendered speculatively while loading; the release header has no re-download path. Absent releases offer **Download album/single/EP**; partial releases offer **Download full album/single/EP**. Link track selection still offers **Download selected**. No replacement completion panel is added.

Artist pages label downloaded local releases **Library** and the provider release shelf **Discography**. Only inspected provider availability is published, so owned releases do not flash briefly before being excluded. Album/Single/EP/Playlist cover badges appear on hover or keyboard focus across Home, Library and release cards. Green card download actions share the play action's glow.

Release types come from exact provider resources (including canonical Spotify entities for search-unlisted editions), with known embedded tags as a Library fallback. They are never inferred from local track counts. Format pills report actual existing files. A bounded, temporary proof cache can recognize alternate Spotify IDs only when independently fetched complete edition sequences agree in ordered titles, credits, album identity, durations, explicit flags and positions. It neither rewrites file/source bindings nor performs provider calls during availability rendering; missing evidence remains unmatched.

Artist names are not split at commas: `Tyler, The Creator` is one artist link. Structured artist credits are kept as individual names and displayed with comma separators, just as on the source page. The metadata source is independent of the audio download source.

Provider-scoped track, artist and release IDs take priority when available. An explicitly opened Spotify album ID or an edition chosen in the existing menu is authoritative: it cannot silently fall back to a different same-title release. Menu/route choices are remembered per signed-in user and exact library album. Failed selections clear the prior expanded source, and selected source artwork/year follow the tracks without changing local tags. Existing file bindings are not rewritten to make another edition look downloaded. Preference saves are serialized so the latest choice wins.

Fallback identity preserves punctuation, symbols, accents and version text (NFKC, lowercase and whitespace normalization only): `|||`, `||`, `!!!`, `+++`, `AC/DC` and `ACDC` are not interchangeable. Conflicting known IDs must not fall back to a same-title match. Ambiguous local matches return no file instead of choosing another artist's recording. Mobile sync uses the same structured credit boundaries.

Artist discography shelves retain underlying provider release IDs while grouping proven duplicate editions in presentation. Explicit/clean and standard/deluxe editions remain separate; same track count alone does not establish a duplicate. Edition menus use meaningful labels rather than ID suffixes and disappear when only one distinct version remains. Owning CHROMAKOPIA does not hide CHROMAKOPIA +. The artist's **Available to download** section excludes fully physically downloaded releases, but keeps partial, missing and removed releases. Library cover cards use the same Album/Single/EP badge as artist cards, without a per-cover hide-from-users menu. Spotify pagination preserves successful pages after a later failure, and artist responses include `discography_status` to distinguish complete results from a capped or fallback overview; partial responses can be retried when reopening the Albums tab.

YouTube audio matching also requires artist evidence and rejects contradictory known YouTube artist IDs. A title/duration match alone is not enough for a supplied artist, including names made entirely of symbols. If no candidate passes the checks, downloading fails rather than substituting a different artist. These checks reduce mismatches but cannot certify that an upstream uploader labelled the audio honestly.

Legacy files without structured credits keep comma-containing names intact. If an older structured list accidentally split the album artist, consecutive fragments are recombined only when they exactly match the tagged album artist; unrelated guest credits are not guessed. Updating the metadata cache does not rewrite audio files or their tags.

### Streaming and undownloaded Spotify album credits

Album resolution also reads the requested Spotify album's public canonical page for structured artist entities. These names and ordered artist IDs are matched to the existing embed rows by exact track identity and compatible title/full-credit text, so collaborations get separate links before downloading while a literal name such as `Tyler, The Creator` remains one link. This is album-level metadata retrieval, not a network request per rendered track. It does not change the selected edition, reorder or drop tracks, download audio, or rewrite existing tags.

If Spotify's canonical state is unavailable, malformed, incomplete or conflicting, unmatched rows retain the safe existing fallback; comma boundaries are never guessed. Exact structured provider credits take precedence over weaker cached subtitles. Spotify playlists continue to use their existing bulk paginated structured metadata, with opaque fallback if that source is unavailable.

### Explicit artist-credit repair

`POST /api/library/artist-credits/repair` is admin-only and defaults to a dry run. An explicit `dry_run: false` can repair selected ID3v2.4 `ARTISTS` lists after validating the original file SHA-256 and preserving the full comma-joined display credit. It backs up each original file and plan under `/data/artist-credit-repair-backups/`, preserves file size, audio bytes, unrelated tags, ownership and modification time, then refreshes the per-file metadata cache. After a repair, call `GET /list?refresh=true` to rebuild the existing Library snapshot before verifying the UI. It does not rename files or download audio.

The same maintenance request can store verified `source_tracks` by exact Spotify track ID in the existing track metadata cache. Album/link views use those structured credits only when the track name and full credit text agree, without per-track network requests while rendering.

## Library page

The Library page has four tabs — **Albums**, **Artists**, **Playlists** and **Tracks**:

- **Albums, artists and playlists** show as a cover grid or a compact list (the toggle is remembered), with a text filter and sorting by recently added, name, artist, year or number of tracks. Albums and artists are built from each file's tags (album artist, album, year), so they don't depend on how files are organized on disk. A track whose album artist is `Various Artists` is grouped by the artist tag instead, so duo names like `Zé Neto & Cristiano` show under that name. A track without an album tag appears under Tracks and its artist, not under Albums.
- **Playlists** are the downloaded playlists with an [M3U file](m3u-export.md), playlists you create with **New playlist** (editable), plus tracked [playlist downloads](slskd-navidrome.md#playlist-downloads) that don't have an M3U yet. Imported Spotify/YouTube playlists stay read-only until you [detach](#detach-an-imported-playlist) them. Playlists other people [share with you](users.md#sharing-playlists) are listed under the grid, apart from your own. Once you have [liked](liked-songs.md) a song, *Liked songs* is listed first. A playlist you created uses a mosaic of up to four track covers; imported playlists keep the artwork saved with the M3U.
- **Tracks** is a sortable table (title, album, format, date added, length) with a text filter, a format filter, and checkboxes — click one, then Shift-click another to select a range. Sort it by clicking a column heading, or with the **Sort by** menu above the table (the only way on a phone, where the headings are hidden): recently added or oldest first, title, artist or album A–Z or Z–A, longest or shortest first. The choice is remembered.

A playlist's songs have the same **Sort by** menu, with **Playlist order** (the playlist's own order, which is where it starts) added to the choices; clicking a column heading works too. **Play** and the song list follow the order you picked, and the choice is remembered, for every playlist.

Opening an album, artist or playlist shows its tracks with **Play**, **Shuffle**, **Add to queue** and **Download as ZIP**. A playlist you created also has **Add songs**, **Rename** and **Share…** (see [sharing playlists](users.md#sharing-playlists)); an imported one has **Share…** and **Detach from source** (below); a downloaded playlist page shows how many of its tracks are downloaded, lists the missing ones with **Download missing**, and offers **Watch for new tracks**. **Delete playlist** is in the **⋯** menu: imported playlists delete the audio; a playlist you created only removes the playlist.

### Detach an imported playlist

A playlist imported from a Spotify or YouTube Music link can't be edited, because Downtify keeps it in step with its source. To tidy one up — drop a song that doesn't belong, add one that does — open it and choose **Detach from source**. It becomes a playlist like the ones you create: its songs and owner stay as they are, and you get **Add songs**, **Rename** and removing songs. In exchange the link to its source is cut: it is no longer updated from Spotify or YouTube Music, its [Playlist Monitor](playlist-monitor.md) watch (if it had one) is removed, and its "missing songs" tracking goes. Songs already downloaded are never touched, and its artwork stays until your first edit, when a mosaic of its songs replaces it. Detaching can't be undone from the app; downloading the link again makes a new imported playlist.

Every account sees the same library: what an admin [hides from users](users.md#hiding-from-users) is left out for them, and an admin sees it all with a crossed-out eye on what is hidden. Admins hide and show from the `…` menu of a song, album or artist, or from the selection bar in **Tracks**.

**Download as ZIP** saves the selected tracks to the device you're browsing from as a single ZIP, keeping their folder layout — handy when Downtify runs on a home server and you want a batch of tracks locally. Combine it with **Select all** to take everything the current filter shows. The archive is built while it downloads, so nothing is written to the server's disk, and it's capped at 2000 tracks per download.

## API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/list?refresh=true` | Library paths, bypassing the path scan cache |
| `GET` | `/api/library/summary` | Home page counts and recent albums, without the full track list |
| `GET` | `/api/library/albums` | Album tiles (counts + cover file), without every track |
| `GET` | `/api/library/artists` | Artist tiles (counts + cover file) for Library and Discover |
| `GET` `POST` | `/api/library/visibility` | Admins: what is hidden from users, and hide / show items |
| `POST` | `/api/library/lookup` | Library rows for search/link songs already downloaded |
| `GET` | `/tracks` | Library tracks with tags. `?playlist=`, `?artist=`, `?album=`, `?q=` and `?limit=` return a subset |
| `GET` | `/media/{path}` | Serve a library file, including `slskd/…` and `ext/…` paths |
| `GET` | `/playlist-cover?file=…` | Serve a playlist's own [cover art](playlist-cover-art.md), reported as `cover` by `/playlists` |
| `POST` | `/api/library/archive` | Prepare a ZIP of selected tracks (returns a single-use ticket) |
| `GET` | `/api/library/archive/{token}` | Stream that ZIP to the browser |
| `DELETE` | `/api/library/playlist?playlist_name=…` | Delete an imported playlist's tracks, M3U and catalog — or only the M3U of a playlist you created |
| `POST` | `/api/library/playlists` | Create an empty editable playlist |
| `POST` | `/api/library/playlists/tracks` | Add or remove library files on a playlist you created |
| `POST` | `/api/library/playlists/rename` | Rename a playlist you created |
| `PUT` | `/api/library/playlists/visibility` | [Share a playlist](users.md#sharing-playlists) you own, view-only |
| `POST` | `/api/library/playlists/copy` | Save a copy of a playlist you can open as an editable one of your own |
| `POST` | `/api/library/playlists/detach` | Turn an imported playlist into an editable one |
| `POST` | `/api/library/reconcile` | Fix library paths, then refresh M3U/Navidrome playlists |
| `POST` | `/api/library/external/sync` | Start a background scan of extra music folders |
| `GET` | `/api/library/external/sync` | Running extra-folder sync, or the last finished log |
| `POST` | `/api/library/external/unmap` | Drop an extra folder from the library without deleting audio |
| `GET`/`POST` | `/api/library/upgrade…` | Scan and repair what is already downloaded — see [Upgrade library](library-upgrade.md#api) |

See the [API reference](../api-reference.md#library) for request and response shapes.
