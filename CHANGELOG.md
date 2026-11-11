# Changelog

## 0.1.2

- Prepare public installation, compatibility, contribution and publication documentation. No runtime selection rules changed.

## 0.1.1

- Run automatic edition selection only for the first complete match of a loaded album.
- Preserve explicit release selections from Other versions and Picard's release-selection dialog, including refreshes and merges into an existing album.
- Invalidate pending selection callbacks immediately on manual choice; keep year-only formatting for the selected edition.
- Restore the intercepted Picard switch method when disabling the plugin, without replacing another plugin's later wrapper.
- Add regression tests for first-check behavior, manual changes during retrieval, merge targets and lifecycle cleanup.

## 0.1.0

- Initial implementation for Picard 3.0.2.
- Experimental release; live Lookup and audio-save validation remain necessary.
