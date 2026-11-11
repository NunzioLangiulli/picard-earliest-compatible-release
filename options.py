"""English options for automatic, year-only release selection."""
from PyQt6.QtWidgets import QCheckBox, QLabel, QVBoxLayout
from picard.plugin3.api import OptionsPage

DEFAULTS = dict(automatic=True, same_format=False, year_only=True)


class Settings(OptionsPage):
    NAME = 'earliest_compatible_release'
    TITLE = 'Earliest Compatible Release'
    PARENT = 'plugins'

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('Earliest Compatible Release 0.1.2 | Author: Borunzio'))
        self.controls = {}
        for key, text in [('automatic', 'Prefer the earliest compatible release on the first Lookup'),
                          ('same_format', 'Require the same medium format on each disc'),
                          ('year_only', 'Write only the selected release year to date')]:
            box = QCheckBox(text)
            layout.addWidget(box)
            self.controls[key] = box
        for text in [
            'Runs once for each newly loaded album after the album finishes loading and every track has at least one matched file, '
            'with no unmatched files left on the album. A choice made in Other versions is kept for the rest of that loaded album session, including refreshes. Remove and reload the album to start a new automatic check.',
            'Only official releases in the same release group are considered. Each disc must have exactly the same recording IDs '
            'in the same order. Equal track counts alone are not enough. Pregaps, data tracks and incomplete recording data are skipped.',
            'Only the year matters: 1993, 1993-02 and 1993-02-05 are equal. The current edition wins a year tie. '
            'Unknown candidate years and pseudo-releases are excluded. If the current year is unknown, the earliest dated compatible '
            'official edition can be selected. Equal-year alternatives are resolved by MusicBrainz ID for repeatability.',
            'Changing edition reloads its metadata and may change artwork and other release details. It does not save audio files. '
            'This chooses an earlier matching track list, not proof of the same mastering or physical pressing. '
            'Network failure leaves the current edition selected. Completion and skip reasons appear in the Picard log.',
        ]:
            label = QLabel(text)
            label.setWordWrap(True)
            layout.addWidget(label)
        layout.addStretch()

    def load(self):
        for key, control in self.controls.items():
            control.setChecked(self.api.plugin_config[key])

    def save(self):
        for key, control in self.controls.items():
            self.api.plugin_config[key] = control.isChecked()

    def restore_defaults(self):
        for key, control in self.controls.items():
            control.setChecked(DEFAULTS[key])
