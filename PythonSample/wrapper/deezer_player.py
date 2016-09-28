#!/usr/bin/python
# coding: utf8

"""
    Deezer ``player`` module for NativeSDK
    ==========================================

    Manage music, load and play songs, reports player events.

    This is a part of the Python wrapper for the NativeSDK. This module wraps
    the deezer-player functions into several python classes. The calls to the
    C lib are done using ctypes.

    Content summary
    ---------------

    The class used to manage the player is the Player class. The others
    describe C enums to be used in callbacks (see below) and logs as
    events (like the PlayerEvent class).

    Callback types
    --------------

    A bunch of this module's functions use callbacks to react to some
    connection events or to process some data. you are free to pass your funcs
    as callbacks, they are then translated to C functions and passed to the SDK
    functions:

        dz_player_on_event_cb:
            Used to handle player state changes, just as
            dz_connect_on_event_cb. See connection module documentation for
            details.

        dz_activity_operation_cb:
            Same as those used in connection module. See connection module
            for details.

"""

from wrapper.deezer_connect import *


class PlayerInitFailedError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class PlayerRequestFailedError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class PlayerActivationError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class PlayerIndex:
    """
        Defines track position in queuelist

        Warning: If you happen to change the values, make sure they correspond
        to the values of the corresponding C enum
    """
    def __init__(self):
        pass

    INVALID = 2 ** 32 - 1,
    CURRENT = 2 ** 32 - 2,
    PREVIOUS = 2 ** 32 - 3,
    NEXT = 2 ** 32 - 4


class PlayerEvent:
    """
        Defines values associated to player events returned by get_event.
        Use it for your callbacks.

        Warning: If you happen to change the values, make sure they correspond
        to the values of the corresponding C enum
    """
    def __init__(self):
        pass

    (
        UNKNOWN,
        LIMITATION_FORCED_PAUSE,
        QUEUELIST_LOADED,
        QUEUELIST_NO_RIGHT,
        QUEUELIST_TRACK_NOT_AVAILABLE_OFFLINE,
        QUEUELIST_TRACK_RIGHTS_AFTER_AUDIOADS,
        QUEUELIST_SKIP_NO_RIGHT,
        QUEUELIST_TRACK_SELECTED,
        QUEUELIST_NEED_NATURAL_NEXT,
        MEDIASTREAM_DATA_READY,
        MEDIASTREAM_DATA_READY_AFTER_SEEK,
        RENDER_TRACK_START_FAILURE,
        RENDER_TRACK_START,
        RENDER_TRACK_END,
        RENDER_TRACK_PAUSED,
        RENDER_TRACK_SEEKING,
        RENDER_TRACK_UNDERFLOW,
        RENDER_TRACK_RESUMED,
        RENDER_TRACK_REMOVED
    ) = range(0, 19)

    @staticmethod
    def event_name(event):
        event_names = [
            u'UNKNOWN',
            u'LIMITATION_FORCED_PAUSE',
            u'QUEUELIST_LOADED',
            u'QUEUELIST_TRACK_NO_RIGHT',
            u'QUEUELIST_TRACK_NOT_AVAILABLE_OFFLINE',
            u'QUEUELIST_TRACK_RIGHTS_AFTER_AUDIOADS',
            u'QUEUELIST_SKIP_NO_RIGHT',
            u'QUEUELIST_TRACK_SELECTED',
            u'QUEUELIST_NEED_NATURAL_NEXT',
            u'MEDIASTREAM_DATA_READY',
            u'MEDIASTREAM_DATA_READY_AFTER_SEEK',
            u'RENDER_TRACK_START_FAILURE',
            u'RENDER_TRACK_START',
            u'RENDER_TRACK_END',
            u'RENDER_TRACK_PAUSED',
            u'RENDER_TRACK_SEEKING',
            u'RENDER_TRACK_UNDERFLOW',
            u'RENDER_TRACK_RESUMED',
            u'RENDER_TRACK_REMOVED'
        ]
        return event_names[event]


class PlayerCommand:
    """Defines commands to update player's state

    Warning: If you happen to change the values, make sure they correspond
    to the values of the corresponding C enum
    """

    def __init__(self):
        pass

    (
        UNKNOWN,
        START_TRACKLIST,
        JUMP_IN_TRACKLIST,
        NEXT,
        PREV,
        DISLIKE,
        NATURAL_END,
        RESUMED_AFTER_ADS
    ) = range(0, 8)


class Player:
    """A simple player load and play music.

        Attributes:
            connection          A connection object to store connection info
            dz_player           The ID of the player
            current_track       The track currently played
            active              True if the player has been activated
    """
    def __init__(self, context, connection):
        """
        :param connection: A connection object to store connection info
        :type connection: connection.Connection
        """
        self.context = context
        self.connection = connection
        self.dz_player_handle = 0
        self.current_content = None
        self.active = False
        self.dz_player_handle = libdeezer.dz_player_new(self.connection.connect_handle)
        if not self.dz_player_handle:
            raise PlayerInitFailedError(u"Player failed to init. Check that connection is established.")
        self._activate(self.context)

    def _activate(self, supervisor=None):
        """Activate the player.

        :param supervisor: An object that can be manipulated by your
            dz_player_on_event_cb to store info.
        :type supervisor: Same as delegate in dz_player_on_event_cb
        """
        context = py_object(supervisor) if supervisor else c_void_p(0)
        if libdeezer.dz_player_activate(self.dz_player_handle, context):
            raise PlayerActivationError(u"Player activation failed. Check player info and your network connection.")
        self.active = True

    def set_event_cb(self, cb):
        """
        Set dz_player_on_event_cb that will be triggered anytime the player
        state changes.

        :param cb: The event callback to give.
        :type cb: dz_on_event_cb_func
        """
        if libdeezer.dz_player_set_event_cb(self.dz_player_handle, cb):
            raise PlayerRequestFailedError(
                u"set_event_cb: Request failed. Check the given callback arguments and return types and/or the player.")

    # TODO: public load function, and use event LOADED to play song
    def load(self, content=None, activity_operation_cb=None, operation_user_data=None):
        """Load the given track or the current track.

        In the first case, set the current_track to the given track.

        :param content: The track/tracklist to load
        :param activity_operation_cb: A callback triggered after operation.
        See module docstring.
        :param operation_user_data:  Any object your operation_callback can
        manipulate. Must inherit from Structure class.
        :type content: str
        :type activity_operation_cb: dz_activity_operation_cb_func
        :type operation_user_data: Same as operation_user_data in your
        callback. Must inherit from Structure as it is used by ctypes
        """
        if content:
            self.current_content = content
        context = byref(operation_user_data) if operation_user_data else c_void_p(0)
        cb = byref(dz_activity_operation_cb_func(activity_operation_cb)) if activity_operation_cb else c_void_p(0)
        if libdeezer.dz_player_load(self.dz_player_handle, cb, context, self.current_content):
            raise PlayerRequestFailedError(u"load: Unable to load selected track. Check connection and tracklist data.")

    # TODO: enum for commands end indices
    def play(self, command=1, index=0, activity_operation_cb=None, operation_user_data=None):
        """Play the current track if loaded.
            The player gets data and renders it.

        :param command: Player command
        :param index: Index of the track to play
        :param activity_operation_cb: Called when async result is available
        :param operation_user_data: A reference to user's data
        :type command: PlayerCommand
        :type index: int
        :type activity_operation_cb: dz_activity_operation_cb_func
        :type operation_user_data: Same as operation_user_data in your callback.
            Must inherit from structure as it is used by ctypes.
        """
        context = byref(operation_user_data) if operation_user_data else c_void_p(0)
        cb = byref(dz_activity_operation_cb_func(activity_operation_cb)) if activity_operation_cb else c_void_p(0)
        if libdeezer.dz_player_play(self.dz_player_handle, cb, context, command, index) not in range(0, 2):
            raise PlayerRequestFailedError(u"play: Unable to play selected track. Check player commands and info.")

    def shutdown(self):
        """
        Deactivate the player and close the connection.
        """
        if self.dz_player_handle:
            libdeezer.dz_player_deactivate(self.dz_player_handle, c_void_p(0), None)
            self.active = False

    # TODO: load and play are independent
    def launch_play(self):
        """
        Load and play the current track.
        """
        self.load()
        self.play()

    @staticmethod
    def get_event(event_obj):
        return libdeezer.dz_player_event_get_type(c_void_p(event_obj))
