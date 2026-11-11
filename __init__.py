"""MusicBrainz Picard 3 automatic release selection lifecycle."""
_controller = None


def album_metadata(api, album, metadata, release_node):
    _controller.capture(album, release_node)


def added(api, track, file):
    _controller.schedule(track.album)


def removed(api, album):
    _controller.remove(album)


def enable(api):
    global _controller
    from .options import Settings, DEFAULTS
    from .controller import Controller
    for name, value in DEFAULTS.items():
        api.plugin_config.register_option(name, value)
    _controller = Controller(api)
    _controller.install_switch_hook()
    api.register_options_page(Settings)
    api.register_album_metadata_processor(album_metadata, priority=1000)
    api.register_file_post_addition_to_track_processor(added, priority=-1000)
    api.register_album_post_removal_processor(removed)


def disable():
    global _controller
    if _controller:
        _controller.disable()
        _controller = None
