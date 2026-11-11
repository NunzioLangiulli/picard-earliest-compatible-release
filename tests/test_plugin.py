"""Compatibility rules and automatic after-Lookup release selection tests."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('earliest_test_plugin', ROOT / '__init__.py', submodule_search_locations=[str(ROOT)])
plugin = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = plugin
spec.loader.exec_module(plugin)
from earliest_test_plugin.rules import *
from earliest_test_plugin.controller import Controller
from earliest_test_plugin.options import DEFAULTS
from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest
from picard.metadata import Metadata

APP = QApplication.instance() or QApplication([])


def release(identifier='current', date='2003-05-07', recordings=('a', 'b')):
    return {'id': identifier, 'date': date, 'status': 'Official', 'release-group': {'id': 'group'},
        'media': [{'format': 'CD', 'track-count': len(recordings),
                   'tracks': [{'recording': {'id': rid}} for rid in recordings]}]}


class Item:
    def __init__(self, **tags):
        self.metadata = Metadata(tags)
        self.update = Mock()


class RulesTests(unittest.TestCase):
    def test_year_precision(self):
        self.assertEqual([year(s) for s in ('1993', '1993-02', '1993-02-05')], [1993]*3)
        self.assertIsNone(year(''))
        self.assertIsNone(year('0000'))
        self.assertIsNone(year('abc'))

    def test_equal_count_different_recordings_rejected(self):
        self.assertFalse(compatible(release(), release(recordings=('b', 'a'))))
        self.assertFalse(compatible(release(), release(recordings=('a', 'c'))))
        self.assertTrue(compatible(release(), release('older', '1993')))

    def test_disc_layout_and_format(self):
        candidate = release()
        candidate['media'] = [dict(format='CD', **{'track-count': 1, 'tracks': [m]}) for m in candidate['media'][0]['tracks']]
        self.assertFalse(compatible(release(), candidate))
        candidate = release()
        candidate['media'][0]['format'] = 'Cassette'
        self.assertTrue(compatible(release(), candidate))
        self.assertFalse(compatible(release(), candidate, True))

    def test_ties_unknown_year_and_pseudo_release(self):
        pseudo = release('pseudo', '1990')
        pseudo['status'] = 'Pseudo-Release'
        values = [release('same-year', '2003'), release('unknown', ''), pseudo, release('older', '1993')]
        self.assertEqual([r['id'] for r in candidates(release(), values)], ['older'])
        self.assertEqual(candidates(release(date='1993'), [release('same-year', '1993-01-01')]), [])

    def test_missing_ids_and_hidden_tracks(self):
        for key, val in [('pregap', {'recording': {'id': 'z'}}), ('data-tracks', [{'id': 'z'}])]:
            value = release()
            value['media'][0][key] = val
            self.assertIsNone(signature(value))
        self.assertIsNone(signature(release(recordings=('a', None))))


class AutomaticTests(unittest.TestCase):
    def setUp(self):
        self.api = SimpleNamespace(plugin_config=dict(DEFAULTS), logger=Mock(),
            tagger=SimpleNamespace(albums={}, window=None, webservice=Mock()), mb_api=Mock())
        self.controller = Controller(self.api)
        self.album = Item(album='Album', date='2003')
        self.album.id = 'current'
        self.album.loaded = True
        self.album.run_when_loaded = lambda f: f()
        self.album.tracks = []
        for i in range(2):
            track = Item(title=str(i))
            track.files = [Item(title=str(i))]
            self.album.tracks.append(track)
        self.album.get_num_unmatched_files = lambda: 0
        self.album.has_critical_tasks = lambda: False
        self.album.switch_release_version = Mock()
        self.api.tagger.albums['current'] = self.album
        self.requests = []
        self.api.mb_api.get.side_effect = lambda path, cb, **kw: self.requests.append((path, cb, kw)) or object()

    def tearDown(self):
        self.controller.disable()

    def start(self):
        self.controller.capture(self.album, release())
        self.controller.schedule(self.album)
        QTest.qWait(1150)

    def respond_list(self, values):
        self.requests.pop(0)[1]({'releases': values, 'release-count': len(values)}, None, None)

    def test_automatic_switch_requires_recording_check(self):
        self.start()
        self.controller.schedule(self.album)  # Duplicate notification must not cancel an active check.
        self.respond_list([release('older', '1993')])
        self.album.switch_release_version.assert_not_called()
        self.requests.pop(0)[1](release('older', '1993-02-05'), None, None)
        self.album.switch_release_version.assert_called_once_with('older')

    def test_incompatible_then_compatible_and_pagination(self):
        self.start()
        self.requests.pop(0)[1]({'releases': [release('wrong', '1990')], 'release-count': 2}, None, None)
        self.assertEqual(self.requests[0][2]['unencoded_queryargs']['offset'], 1)
        self.requests.pop(0)[1]({'releases': [release('right', '1993')], 'release-count': 2}, None, None)
        self.requests.pop(0)[1](release('wrong', '1990', ('wrong', 'ids')), None, None)
        self.requests.pop(0)[1](release('right', '1993'), None, None)
        self.album.switch_release_version.assert_called_once_with('right')

    def test_partial_album_waits_for_files(self):
        saved = self.album.tracks[1].files.pop()
        self.start()
        self.assertFalse(self.requests)
        self.album.tracks[1].files.append(saved)
        self.controller.schedule(self.album)
        QTest.qWait(1150)
        self.assertTrue(self.requests)

    def test_year_tie_keeps_current_and_writes_only_year(self):
        self.start()
        self.respond_list([release('same-year', '2003')])
        self.album.switch_release_version.assert_not_called()
        self.assertEqual(self.album.tracks[0].files[0].metadata['date'], '2003')
        self.assertFalse(hasattr(self.album, '_borunzio_earliest_pending'))

    def test_failure_and_manual_edit_prevent_switch(self):
        self.start()
        self.respond_list([release('older', '1993')])
        self.album.metadata['album'] = 'Manual edit'
        self.requests.pop(0)[1](release('older', '1993'), None, None)
        self.album.switch_release_version.assert_not_called()
        self.assertFalse(hasattr(self.album, '_borunzio_earliest_pending'))

    def test_network_failure_prevents_switch(self):
        self.start()
        self.requests.pop(0)[1](None, None, 'Network unavailable')
        self.album.switch_release_version.assert_not_called()
        self.assertFalse(hasattr(self.album, '_borunzio_earliest_pending'))

    def test_manual_choice_cancels_inflight_search_and_survives_refresh(self):
        self.start()
        self.controller.record_manual_choice(self.album, 'manual-release')
        self.respond_list([release('older', '1993')])
        self.album.switch_release_version.assert_not_called()
        self.api.tagger.albums.pop('current')
        self.album.id = 'manual-release'
        self.api.tagger.albums[self.album.id] = self.album
        for _ in range(2):
            self.controller.capture(self.album, release('manual-release', '2020-04-05'))
            QTest.qWait(1150)
            self.assertFalse(self.requests)
            self.assertEqual(self.album.metadata['date'], '2020')
        self.album.switch_release_version.assert_not_called()

    def test_finished_first_check_does_not_repeat_on_refresh(self):
        self.start()
        self.respond_list([])
        self.controller.capture(self.album, release())
        QTest.qWait(1150)
        self.assertFalse(self.requests)

    def test_switch_hook_distinguishes_automatic_and_manual_merge(self):
        from picard.album import Album
        from unittest.mock import patch
        target = Item(album='Target')
        self.api.tagger.albums['target'] = target
        with patch.object(Album, 'switch_release_version') as original:
            self.controller.install_switch_hook()
            try:
                self.controller.automatic_switches.add(self.album)
                Album.switch_release_version(self.album, 'older')
                self.assertNotIn(self.album, self.controller.manual)
                self.controller.automatic_switches.discard(self.album)
                Album.switch_release_version(self.album, 'target')
                self.assertIn(self.album, self.controller.manual)
                self.assertIn(target, self.controller.manual)
                self.assertEqual(original.call_count, 2)
            finally:
                self.controller.disable()
                self.assertIs(Album.switch_release_version, original)

    def test_disable_ignores_late_response(self):
        self.start()
        self.controller.disable()
        self.respond_list([release('older', '1993')])
        self.album.switch_release_version.assert_not_called()
        self.assertFalse(self.requests)


if __name__ == '__main__':
    unittest.main(verbosity=2)
