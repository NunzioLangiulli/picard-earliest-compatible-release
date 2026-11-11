# Earliest Compatible Release for MusicBrainz Picard

Automatically prefer the oldest publication year among compatible official editions of a matched album in MusicBrainz Picard. No manual plugin action is required after Lookup.

**Version:** 0.1.2 · **Author:** Borunzio · **License:** MIT

Targets **Picard 3.0.2**. Automated tests use actual Picard components with simulated albums and network callbacks. Verify an album in the installed application before saving a library.

## Installation and use

For installation from GitHub, open **Options → Plugins → Install Plugin**, choose repository URL installation and enter `https://github.com/NunzioLangiulli/picard-earliest-compatible-release`. Select **v0.1.2**, enable the plugin and restart Picard. This URL becomes available after the repository and tag are published. Installing from `main` may show the branch name as the version.

### Local installation

1. Open **Options → Plugins → Install Plugin → Local repository**.
2. Select this repository folder, including its `.git` directory, and choose **v0.1.2**.
3. Enable the plugin and restart Picard.
4. Run Lookup and let Picard match all files to the album. Refresh an album loaded before plugin activation.
5. Wait for the automatic check and any resulting release reload. Review the selected edition and save normally.

The automatic option is enabled by default. There is deliberately no required **Apply now** action. The check runs only once after the initial complete match for each loaded album. A release refresh does not repeat a completed check.

**Your manual selection takes priority.** Choosing an edition from **Other versions** (or Picard's release-selection dialog) cancels pending automatic selection and locks that choice for the loaded album, including later refreshes. The same protection applies if Picard moves your files into an edition already loaded elsewhere. The plugin's own initial switch does not count as a manual choice. The year-only formatting still follows the edition you selected.

Remove the album from Picard and load it again to start a fresh automatic check. Manual-choice protection remains attached to the album if the plugin is disabled and re-enabled during the same Picard session. External release switches from another plugin are conservatively treated as explicit choices as well. This uses an internal Picard release-switch method; compatibility must be rechecked after Picard upgrades.

## Selection rules

- Wait until the release finishes loading, every track has a matched file, and no unmatched files remain on the album. Partial albums are left in place until matching completes.
- Browse every page of releases in the same MusicBrainz release group.
- Consider only **Official** candidates with a known publication year. Exclude pseudo-releases and undated alternatives.
- Compare years only: `1993`, `1993-02` and `1993-02-05` are equal. Month and day never decide precedence.
- Keep the current edition when an alternative has the same year. If the current year is unknown, a dated compatible edition can be selected.
- Require the same number of discs and the same ordered MusicBrainz recording IDs on every disc. Equal track counts alone are not sufficient.
- Reject incomplete recording data, pregaps and data-track layouts that cannot be safely compared by this implementation.
- Optionally require the same medium format on every disc.
- Among earlier compatible alternatives, select the earliest year. Resolve an equal-year tie between alternatives by MusicBrainz ID for repeatable results.

The year comes from the release date, not the release group's `originaldate`. The plugin changes the selected edition through Picard's release-switch mechanism; it is not merely a date-tag replacement.

## Options

Open **Options → Plugins → Earliest Compatible Release**.

| Option | Default | Behavior |
| --- | --- | --- |
| Prefer the earliest compatible release on the first Lookup | Enabled | Runs after loading and file matching, with no menu action. |
| Require the same medium format on each disc | Disabled | When enabled, CD and cassette, for example, cannot substitute for one another. |
| Write only the selected release year to date | Enabled | After a successful check/reload, sets `date` to a four-digit year on the album, tracks and matched files. |

The current edition is retained when there is no earlier compatible candidate. Network errors abort the check rather than choosing an incompletely verified result. A target edition already loaded elsewhere in Picard is not merged automatically. Pending checks are abandoned if metadata or matching changes. Once a check has begun, remove and reload the album to start a new check, including after a network failure.

## What changing an edition means

Picard reloads the selected release and runs its usual metadata, scripting, artwork and matching workflow. That can change release-specific labels, catalogue numbers, artwork and other fields. The plugin does not save audio files, so review the result before using Picard's Save action.

Identical recording IDs do not prove identical mastering, physical pressing or audio encoding. This plugin intentionally follows an oldest-compatible-track-list policy. It cannot establish which physical edition your files came from.

If Bilingual Names is enabled, it waits for this selection to finish and then formats the final release's artist and album names. Both plugins remain independently installable. IDs are read from Picard's loaded MusicBrainz data rather than restored into writable tags.

## Progress and troubleshooting

Check Picard's status bar and **View Error/Debug Log** (**Ctrl+G** on Windows) for messages beginning **Earliest Compatible Release**.

| Result | Explanation |
| --- | --- |
| Waiting for a complete, fully matched album | At least one track is missing a file, unmatched files remain, or the recording layout cannot be verified. |
| No earlier compatible official edition found | No older candidate passed the exact recording/disc-layout checks. |
| Switching to YEAR | A fully checked candidate was selected and Picard is reloading it. |
| No edition changed | A request failed, the target was already loaded, or Picard still had critical loading work. |

The first run can take time for albums with many editions: listing and detailed candidate requests use Picard's MusicBrainz queue. Responses are cached for the plugin session. Restart Picard to clear that cache. Changing options affects new checks; remove and reload an album to retry. Wait for processing to settle before saving.

## Validation

With PyQt6, Picard 3.0.2 source and its dependencies importable, run each test file in its own Python process:

```sh
python -B tests/test_plugin.py
python -B tests/test_lifecycle.py
```

Tests cover year precision, ties, unknown dates, pseudo-release exclusion, recording order, disc layout, optional format matching, partial-album scheduling, pagination, network errors, stale callbacks, manual edits, manual selection during an in-flight lookup, persistence across refreshes, merge targets, reversible release-switch interception, and real plugin loader/options/disable behavior. A combined test in the sibling Bilingual Names repository checks automatic edition switching followed by bilingual formatting without a loop.

Read-only live MusicBrainz requests verified the release-list and release-detail response structure for release group `5214f8d2-138a-333f-b50f-814a61856934`. This does not replace testing a complete Lookup/reload/save cycle in the installed application. Tests do not write audio files.

## Reporting issues and license

Include Picard/plugin versions, current and expected release links, disc/track counts, options and the relevant log excerpt. Remove private paths and do not upload audio files.

[MIT License](LICENSE) · [Changelog](CHANGELOG.md). Independent community plugin by Borunzio.

See [CONTRIBUTING.md](CONTRIBUTING.md) for reports and development, and [PUBLISHING.md](PUBLISHING.md) for manual GitHub publication.
