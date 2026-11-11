"""Real Picard plugin loader and option-page lifecycle; isolated settings only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PyQt6.QtWidgets import QApplication
from picard.album import Album
from picard import config
import picard.options
from picard.plugin3.plugin import Plugin


class LifecycleTests(unittest.TestCase):
    def test_enable_options_and_disable(self):
        app = QApplication.instance() or QApplication([])
        app.window = None
        app.albums = {}
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix='picard-borunzio-test-') as tmp:
            config.setup_config(app, str(Path(tmp) / 'settings.ini'))
            plugin = Plugin(root.parent, root.name)
            plugin.read_manifest()
            module = plugin.load_module()
            original_switch = Album.switch_release_version
            plugin.enable(app)
            self.assertIsNot(Album.switch_release_version, original_switch)
            from importlib import import_module
            options = import_module(module.__name__ + '.options')
            with patch('picard.ui.options.tagger_instance', return_value=app):
                page = options.Settings()
            page.load()
            self.assertTrue(page.controls['automatic'].isChecked())
            page.controls['automatic'].setChecked(False)
            page.check()
            page.save()
            self.assertFalse(module._controller.api.plugin_config['automatic'])
            page.restore_defaults()
            self.assertTrue(page.controls['automatic'].isChecked())
            controller = module._controller
            page.close()
            plugin.disable()
            self.assertIs(Album.switch_release_version, original_switch)
            self.assertFalse(controller.active)
            self.assertIsNone(module._controller)


if __name__ == '__main__':
    unittest.main(verbosity=2)
