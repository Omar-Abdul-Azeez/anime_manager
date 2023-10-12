# -*- encoding:utf-8 -*-
import shlex
import sys
from sys import argv
from argparse import ArgumentParser, ArgumentError
import logging
from configparser import ConfigParser

from anime import *


config = ConfigParser()
config.read('config.ini')
if config.has_section('logging'):
    section = config['logging']
    level = section.get('level', 'INFO')
    if level == 'INFO':
        level = logging.INFO
    elif level == 'DEBUG':
        level = logging.DEBUG
else:
    level = logging.INFO

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler_file = logging.FileHandler('anime.log', encoding='utf-8')
handler_file.setFormatter(formatter)
logger = logging.getLogger('anime')
logger.addHandler(handler_file)
logger.setLevel(level)

formatter_stderr = logging.Formatter('%(levelname)s - %(message)s')
handler_stderr = logging.StreamHandler(sys.stderr)
handler_stderr.setFormatter(formatter_stderr)
handler_stderr.setLevel(logging.WARNING)
logger.addHandler(handler_stderr)


def main():
    parser = ArgumentParser(exit_on_error=False)
    subparsers = parser.add_subparsers(help='Anime library manager. Helps keep library in a uniform structure. folder template: "([anime-id] )?[anime-title]", episode template: "[anime-title] [episode-number].[ext]".')
    auth = subparsers.add_parser('auth', help='Auth mode, use this mode to get/set an authorization token.')
    auth.set_defaults(func=lambda *args, **kwargs: auth.print_help())
    auth_sub = auth.add_subparsers()
    auth_get = auth_sub.add_parser('get', help='Obtain an authorization token.')
    auth_get.set_defaults(func=get_auth)
    auth_set = auth_sub.add_parser('set', help='Authorize using an authorization token.')
    auth_set.set_defaults(func=set_auth)
    auth_set.add_argument('auth', help='Authorization token.')
    library = subparsers.add_parser('library', help='Library mode, covers and renames each anime folder inside a library directory and it\'s episodes to be consistent with Anilist.')
    library.set_defaults(func=tidy_library)
    library.add_argument('root', help='Library directory.', metavar='DIR')
    library.add_argument('-m', '--manual', action='store_false', dest='auto', help='Manual mode, manually choose correct anime from search results of anime folder\'s name', default=True)
    library.add_argument('-o', '--offline', action='store_true', dest='offline', help='Offline mode, disables covering and renaming folders. However, renames episodes so that they follow "[folder-title] [episode-number].[ext]".', default=False)
    library.add_argument('-s', '--shift', action='store_true', dest='shift', help='Shift episode numbers so that they start at 1 instead of some other number like 13. Doesn\'t shift if they start at 0')
    library.add_argument('-l', '--lang', type=Lang, choices=list(Lang), dest='lang', help='Title language to use', default=Lang.NATIVE)
    season = subparsers.add_parser('season', help='Season mode, creates anime folders for each currently-airing anime in the user\'s watching list on Anilist and covers them.')
    season.set_defaults(func=create_watching_dir)
    season.add_argument('root', help='Root directory.', metavar='DIR')
    season.add_argument('-u', '--uid', action='store', dest='uid', help='User ID on Anilist (Defaults to authorized user), refer to this on how to get it. https://anilist.co/forum/thread/63486/comment/2197131')
    season.add_argument('-l', '--lang', type=Lang, choices=list(Lang), dest='lang', help='Title language to use', default=Lang.NATIVE)
    rss = subparsers.add_parser('rss', help='RSS mode, runs watching mode in the specified qbittorrent category\'s save path then modifies qbittorrent\'s rss config to save each anime in it\'s folder directly with no need for guessing.')
    rss.set_defaults(func=update_rss)
    rss.add_argument('-u', '--uid', action='store', dest='uid', help='User ID on Anilist (Defaults to authorized user), refer to this on how to get it. https://anilist.co/forum/thread/63486/comment/2197131')
    rss.add_argument('category', help='Category to use save path of.')
    rss.add_argument('-l', '--lang', type=Lang, choices=list(Lang), dest='lang', help='Title language to use', default=Lang.NATIVE)
    episodes = subparsers.add_parser('episodes', help='Episodes mode, renames all video files in the root directory by guessing which anime in the user\'s watching list is it from.\nIf anime folders already exist by using rss or season modes, renames episodes inside those folders so that they follow "[folder-title] [episode-number].[ext]".')
    episodes.set_defaults(func=tidy_episodes)
    episodes.add_argument('-u', '--uid', action='store', dest='uid', help='User ID on Anilist (Defaults to authorized user, can be omitted if "response.json" exists), refer to this on how to get it. https://anilist.co/forum/thread/63486/comment/2197131')
    episodes.add_argument('root', help='Root directory.', metavar='DIR')
    episodes.add_argument('-s', '--shift', action='store_true', dest='shift', help='Shift episode numbers so that they start at 1 instead of some other number like 13. Doesn\'t shift if they start at 0')
    episodes.add_argument('-l', '--lang', type=Lang, choices=list(Lang), dest='lang', help='Title language to use', default=Lang.NATIVE)
    tsumi = subparsers.add_parser('tsumi', help='Tsumi mode (Requires authorization), adds yet-to-be-watched anime in library to Anilist customlist and removes completed anime from it. (completed anime needs to be in the library)')
    tsumi.set_defaults(func=update_tsumi)
    tsumi.add_argument('customlist', help='Custom list\'s name on Anilist.')
    tsumi.add_argument('root', help='Library directory. Defaults to current directory', metavar='DIR')
    tsumi.add_argument('-a', '--auth', action='store', dest='auth', help='Authorization token (Can be omitted if authorized using Auth mode), refer to Auth mode to obtain one.')
    if len(argv) == 1:
        # parser.print_help()
        print('Running in console mode. Enter "exit" to exit.')
        inp = input('>')
        while inp != 'exit':
            try:
                args = parser.parse_args(shlex.split(inp))
                command_args = vars(args).copy()
                del command_args['func']
                args.func(**command_args)
            except ArgumentError as e:
                parser.print_help()
            inp = input('>')
    else:
        try:
            args = parser.parse_args(argv[1:])
            command_args = vars(args).copy()
            del command_args['func']
            args.func(**command_args)
        except ArgumentError as e:
            parser.print_help()
