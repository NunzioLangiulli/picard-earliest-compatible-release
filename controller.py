"""Automatically select the oldest compatible official release after Lookup."""
from weakref import WeakSet
from functools import wraps
from .runtime import Runtime, files, snapshot
from .rules import candidates, compatible, signature, year


class Controller(Runtime):
    def __init__(self, api):
        super().__init__(api)
        self.switching = set()
        self.checked = WeakSet()
        self.manual = WeakSet()
        self.automatic_switches = WeakSet()
        self.switch_hook = None

    def install_switch_hook(self):
        from picard.album import Album
        self.original_switch = Album.switch_release_version
        original = self.original_switch
        @wraps(original)
        def switch(album, mbid):
            if self.active and album not in self.automatic_switches:
                self.record_manual_choice(album, mbid)
            return original(album, mbid)
        self.switch_hook = switch
        Album.switch_release_version = switch

    def record_manual_choice(self, album, mbid):
        # Lock the target too: Picard can merge into an already loaded release.
        target = self.api.tagger.albums.get(mbid)
        for item in (album, target):
            if item is not None:
                item._borunzio_manual_release = True
                self.manual.add(item)
                self.tokens[item] = object()
                self.finish(item)
        self.message('Earliest Compatible Release: keeping the manually selected edition for this loaded album.')

    def switch_automatically(self, album, mbid):
        self.automatic_switches.add(album)
        try:
            album.switch_release_version(mbid)
        finally:
            self.automatic_switches.discard(album)

    def capture(self, album, node):
        if getattr(album, '_borunzio_manual_release', False):
            self.manual.add(album)
        previous = self.nodes.get(album)
        if (previous and previous.get('id') != node.get('id')
                and node.get('id') not in self.switching):
            self.record_manual_choice(album, node.get('id'))
        # Bilingual Names must also wait for year formatting after a reload.
        album._borunzio_earliest_pending = self
        super().capture(album, node)

    def finish(self, album):
        if getattr(album, '_borunzio_earliest_pending', None) is self:
            del album._borunzio_earliest_pending

    def remove(self, album):
        self.manual.discard(album)
        self.checked.discard(album)
        if hasattr(album, '_borunzio_manual_release'):
            del album._borunzio_manual_release
        self.finish(album)
        super().remove(album)

    def disable(self):
        from picard.album import Album
        if self.switch_hook is not None and Album.switch_release_version is self.switch_hook:
            Album.switch_release_version = self.original_switch
        for album in list(self.nodes):
            self.finish(album)
        super().disable()

    def start(self, album, token):
        album._borunzio_earliest_pending = self
        current = self.nodes[album]
        if album in self.manual or album in self.checked:
            self.switching.discard(album.id)
            self.set_year(album)
            self.finish(album)
            return
        if album.id in self.switching:
            self.switching.discard(album.id)
            self.set_year(album)
            self.finish(album)
            return
        if (not signature(current) or not album.tracks
                or any(not track.files for track in album.tracks)
                or album.get_num_unmatched_files()):
            self.finish(album)
            self.message('Earliest Compatible Release: waiting for a complete, fully matched album.')
            return
        group_id = current.get('release-group', {}).get('id')
        if not group_id:
            self.finish(album)
            return
        self.checked.add(album)
        release_id = album.id
        original_snapshot = snapshot(album)
        same_format = self.api.plugin_config['same_format']
        releases = []

        def valid():
            result = (album not in self.manual and self.valid(album, token) and album.id == release_id
                    and getattr(album, 'loaded', False)
                    and self.api.plugin_config['same_format'] == same_format
                    and snapshot(album) == original_snapshot)
            if not result and self.tokens.get(album) is token:
                self.finish(album)
            return result

        def failed(error):
            self.finish(album)
            self.message('Earliest Compatible Release: no edition changed. ' + str(error))

        def choose(queue):
            if not valid():
                return
            if not queue:
                self.set_year(album)
                self.finish(album)
                self.message('Earliest Compatible Release: no earlier compatible official edition found.')
                return
            candidate = queue.pop(0)
            def received(document, error):
                if not valid():
                    return
                if error:
                    failed(error)
                    return
                if (document.get('status') == 'Official'
                        and year(document.get('date')) == year(candidate.get('date'))
                        and compatible(current, document, same_format)):
                    # Switching an already loaded target could merge independently edited albums.
                    if document['id'] in self.api.tagger.albums:
                        failed('The earlier edition is already loaded; keeping albums separate.')
                        return
                    if album.has_critical_tasks():
                        failed('Picard is still loading critical album data; refresh later to retry.')
                        return
                    self.switching.add(document['id'])
                    self.message('Earliest Compatible Release: switching to ' + str(year(document['date']))
                                 + ' (' + document['id'] + ').')
                    self.finish(album)
                    self.switch_automatically(album, document['id'])
                else:
                    choose(queue)
            self.request('/release/' + candidate['id'],
                         {'inc': 'recordings+release-groups+media'}, received)

        def browse(offset=0):
            def received(document, error):
                if not valid():
                    return
                if error:
                    failed(error)
                    return
                page = document.get('releases', [])
                if not isinstance(page, list):
                    failed('Invalid release list.')
                    return
                releases.extend(page)
                total = document.get('release-count', len(releases))
                if len(releases) < total:
                    if not page:
                        failed('Incomplete MusicBrainz release list.')
                        return
                    browse(offset + len(page))
                else:
                    choose(candidates(current, releases))
            self.request('/release', {'release-group': group_id, 'inc': 'media', 'limit': 100, 'offset': offset}, received)
        browse()

    def set_year(self, album):
        if not self.api.plugin_config['year_only']:
            return
        value = year(self.nodes[album].get('date'))
        if value is None:
            return
        for item in [album] + list(album.tracks) + files(album):
            item.metadata['date'] = str(value)
            if item is not album:
                item.update()
        album.update()
