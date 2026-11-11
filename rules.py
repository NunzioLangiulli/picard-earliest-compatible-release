"""Conservative release compatibility and year-only ordering."""
import re


def year(value):
    match = re.match(r'^(\d{4})(?:-|$)', str(value or ''))
    return int(match[1]) if match and 0 < int(match[1]) < 10000 else None


def signature(release):
    """Require the same ordered recording IDs on each medium; reject incomplete data."""
    media = release.get('media') or []
    if not media:
        return None
    result = []
    for medium in media:
        tracks = medium.get('tracks') or []
        if (not tracks or len(tracks) != medium.get('track-count')
                or medium.get('pregap') or medium.get('data-tracks')):
            return None
        ids = tuple(t.get('recording', {}).get('id') for t in tracks)
        if not all(ids):
            return None
        result.append(ids)
    return tuple(result)


def compatible(current, candidate, same_format=False):
    expected = signature(current)
    if expected is None or signature(candidate) != expected:
        return False
    if current.get('release-group', {}).get('id') != candidate.get('release-group', {}).get('id'):
        return False
    if same_format:
        return [m.get('format') for m in current['media']] == [m.get('format') for m in candidate['media']]
    return True


def candidates(current, releases):
    current_year = year(current.get('date'))
    expected_counts = tuple(len(m) for m in signature(current) or ())
    found = {}
    for release in releases:
        y = year(release.get('date'))
        counts = tuple(m.get('track-count') for m in release.get('media', []))
        if (release.get('id') and release['id'] != current.get('id')
                and release.get('status') == 'Official' and y is not None
                and (current_year is None or y < current_year)
                and counts == expected_counts):
            found[release['id']] = release
    return sorted(found.values(), key=lambda r: (year(r['date']), r['id']))
