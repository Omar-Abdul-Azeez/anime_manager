# -*- encoding:utf-8 -*-
import logging
import json
import os
import subprocess
import sys

import natsort
import regex
import math

from rapidfuzz import process
from rapidfuzz import fuzz

logger_module = logging.getLogger('anime')


logger_io = logger_module.getChild('io')
logger_io.addHandler(logging.NullHandler())

formatter_regex = logging.Formatter('%(asctime)s - %(message)s')
handler_regex = logging.FileHandler('regex.log', encoding='UTF8')
handler_regex.setFormatter(formatter_regex)
logger_regex = logger_module.getChild('regex')
logger_regex.addHandler(handler_regex)
logger_regex.setLevel(logging.DEBUG)
logger_regex.propagate = False
def audit_os(event, args):
    if event.startswith('os.') or event == 'open':
        logger_io.debug('%s happened with args %s', event, args)

sys.addaudithook(audit_os)

from anime import app, anilist_api
from anime.network import scrape
from anime.enums import Lang
from anime.rules import related_exts, pattern_id, pattern_se, pattern_ex, pattern_se_groups, ep_filename


def walklevel(path, depth=1):
    """It works just like os.walk, but you can pass it a level parameter
           that indicates how deep the recursion will go.
           If depth is 1, the current directory is listed.
           If depth is 0, nothing is returned.
           If depth is -1 (or less than 0), the full depth is walked.
        """
    from os.path import sep
    from os import walk
    # If depth is negative, just walk
    # and copy dirs to keep consistent behavior for depth = -1 and depth = inf
    if depth < 0:
        for root, dirs, files in walk(path):
            yield root, dirs[:], files
        return
    elif depth == 0:
        return

    base_depth = path.rstrip(sep).count(sep)
    for root, dirs, files in walk(path):
        yield root, dirs[:], files
        cur_depth = root.count(sep)
        if base_depth + depth <= cur_depth:
            del dirs[:]


dquotes = [('「', '」'), ('『', '』'), ('“', '”')]
def special_chars(string, replace=False, dquotes=dquotes[2]):
    # \/:*?"<>|
    # WON'T REPLACE <> AND F NTFS (actually haven't encountered yet（；ﾟдﾟ）ｺﾁｺﾁ)
    if string.endswith('.'):
        # print(f'TRAILING PERIOD（；ﾟдﾟ）ﾋｨｨｨ Title: {string}')
        string = string[:-1]
    if replace:
        lis = []
        flag = False
        for c in string:
            if c == '<' or c == '>':
                print(f'<> IN TITLE（；ﾟдﾟ）ﾋｨｨｨ Title: {string}')
                input()
                raise ValueError
            elif c == '\\':
                lis.append('＼')
            elif c == '/':
                lis.append('／')
            elif c == ':':
                lis.append('：')
            elif c == '?':
                lis.append('？')
            elif c == '*':
                lis.append('＊')
            elif c == '|':
                lis.append('｜')
            elif c == '"':
                lis.append(dquotes[0] if (flag := not flag) else dquotes[1])
            else:
                lis.append(c)
        return ''.join(lis)
    else:
        return ''.join([c for c in string if c not in {'\\', '/', ':', '*', '?', '"', '<', '>', '|'}])


def backup(src, dst_dir):
    import shutil
    import os
    if os.path.exists(os.path.join(dst_dir, os.path.basename(src) + '.bak')):
        i = 1
        while os.path.exists(os.path.join(dst_dir, os.path.basename(src) + '.bak' + str(i))):
            i = i + 1
        shutil.move(src, os.path.join(dst_dir, os.path.basename(src) + '.bak' + str(i)))
    else:
        shutil.move(src, os.path.join(dst_dir, os.path.basename(src) + '.bak'))


def create_icon(pic, icon):
    from PIL import Image
    img = Image.open(pic)
    w, h = img.size
    size = max(256, w, h)
    ico = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    ico.paste(img, (int((size - w) / 2), int((size - h) / 2)))
    img.close()
    if os.path.exists(icon):
        os.remove(icon)
    ico.save(icon)
    ico.close()


def cover_folder(pic, root, title):
    create_icon(pic, os.path.join(root, title + ".ico"))
    if os.path.exists(os.path.join(root, "desktop.ini")):
        os.remove(os.path.join(root, "desktop.ini"))
    with open(os.path.join(root, "desktop.ini"), "w", encoding="utf-16 le") as f:
        f.write(u'\ufeff')
        f.write("[.ShellClassInfo]\nConfirmFileOp=0\n")
        f.write(f"IconResource={title}.ico,0")
        f.write(f"\nIconFile={title}.ico\nIconIndex=0")
    subprocess.check_call('attrib +r \"{}\"'.format(root))
    subprocess.check_call('attrib +h \"{}\"'.format(os.path.join(root, "desktop.ini")))
    subprocess.check_call('attrib +h \"{}\"'.format(os.path.join(root, title + ".ico")))


def extract_episode_number(file, title=None, log=False):
    ptn_se = regex.compile(pattern_se, regex.IGNORECASE)
    ptn_ex = regex.compile(pattern_ex, regex.IGNORECASE)
    file_edited = file
    if log:
        logger_regex.info('String: %s', file_edited)
    if title is not None:
        file_edited = regex.sub(regex.compile(r'[. x_-]?'.join(map(regex.escape, regex.sub(regex.compile(r'[_-]'), ' ', title).split()))), '', file_edited)
        if log:
            logger_regex.info('Title to remove: %s', title)
            logger_regex.info('Result: %s', file_edited)
    file_edited = regex.sub(ptn_ex, '', file_edited)
    if log:
        logger_regex.info('Cleaned-up result: %s', file_edited)
    matches = list(regex.finditer(ptn_se, file_edited, overlapped=True))
    if log:
        logger_regex.info('Matches: %s', matches)
    groups_num = list(map(lambda match: sum(map(lambda group: 0 if group is None else 1, match.groups())), matches))
    if log:
        logger_regex.info('Groups counts: %s', groups_num)
    matches = list(reversed(matches))[list(reversed(groups_num)).index(max(groups_num))]
    file_edited = file_edited[:matches.start()] + file_edited[matches.end():]
    if log:
        logger_regex.info('Remaining: %s', file_edited)
    matches = pattern_se_groups(matches.groups())
    if log:
        logger_module.debug('Extracted Season: %s Episode: %s', *matches)
        logger_regex.info('_'*40)
    return *matches, file_edited


def ep_follows_template(string, title, ext, lang, digits=None):
    num = r'(\d+(-\d+)*)'
    if digits:
        num = r'\d'*digits
        num = '(' + num + '(-' + num + ')*)'
    pattern = ep_filename(regex.escape(title), num, regex.escape(ext), lang)
    ptn = regex.compile(pattern)
    match = regex.fullmatch(ptn, string)
    if match:
        return True
    return False


def tidy_library(root='.', offline=False, auto=True, shift=False, lang=Lang.NATIVE):
    if offline:
        logger_module.info('Tidying library in offline mode with lang=%s...', lang)
    else:
        logger_module.info('Tidying library with lang=%s...', lang)

    walkie = walklevel(root, depth=1)
    next(walkie)
    for dir, _, files in walkie:
        folder = os.path.basename(dir)
        logger_module.info('Processing "%s"', folder)
        id = next(filter(lambda x: regex.match(r'^\d+$', x) is not None, files), None)
        if id is not None:
            logger_module.info('Found ID file: "%s"', id)
            if not offline and os.path.exists(os.path.join(dir, "desktop.ini")):
                logger_module.info('"%s" exists. Skipping.', os.path.join(dir, "desktop.ini"))
                continue
        ptn_id = regex.compile(pattern_id)
        match_id = regex.match(ptn_id, folder)
        if match_id is not None:
            match_id = match_id.group(0)
            logger_module.info('Found prepended ID: "%s"', match_id)
            if id is None:
                id = match_id[1:-2]
            elif match_id[1:-2] != id:
                logger_module.warning('Prepended ID "%s" does not match ID file "%s". Skipping.', match_id[1:-2], id)
                continue

        if offline:
            title = os.path.basename(dir) if match_id is None else os.path.basename(dir)[len(match_id):]
            folder = dir
        else:
            if id is not None:
                media = anilist_api.get_anime(ids=int(id))
            else:
                media = anilist_api.get_anime(search=folder, auto=auto, lang=lang)

            id = str(media['id'])
            banner = media['bannerImage']
            cover = media["coverImage"]["extraLarge"]
            if lang is Lang.NATIVE:
                title = media['title']['native']
                if title is None:
                    logger_module.warning('No native title found, falling back to romaji.')
                    title = media['title']['romaji']
                logger_module.info('Chosen: "%s" as title.', title)
                title = special_chars(title, replace=True)
            elif lang is Lang.ROMAJI:
                title = media['title']['romaji']
                logger_module.info('Chosen: "%s" as title.', title)
                title = special_chars(title, replace=False)
            elif lang is Lang.ENGLISH:
                title = media['title']['english']
                if title is None:
                    logger_module.warning('No english title found, falling back to romaji.')
                    title = media['title']['romaji']
                logger_module.info('Chosen: "%s" as title.', title)
                title = special_chars(title, replace=False)
            logger_module.debug('Using "%s" for IO operations.', title)
            if os.path.basename(dir) != title:
                temp = title
                if os.path.exists(os.path.join(root, temp)):
                    temp = f'[{id}] {temp}'
                if os.path.basename(dir) != temp:
                    logger_module.debug('Folder "%s" not "%s"', folder, title if os.path.basename(dir).lower() == temp.lower() else temp)
                    ico_path = os.path.join(dir, (folder if match_id is None else folder[len(match_id):]) + '.ico')
                    if os.path.exists(ico_path):
                        logger_module.debug('Icon with old name exists. Deleting...')
                        os.remove(ico_path)
                    os.renames(dir, os.path.join(root, temp))
                    folder = temp
                    if not os.path.exists(os.path.join(root, title)):
                        os.renames(os.path.join(root, temp), os.path.join(root, title))
                        folder = title

            if not os.path.exists(os.path.join(root, folder, id)):
                open(os.path.join(root, folder, id), 'w').close()
            if not os.path.exists(os.path.join(root, folder, "Cover", ".ignore")):
                if not os.path.exists(os.path.join(root, folder, "Cover")):
                    os.mkdir(os.path.join(root, folder, "Cover"))
                open(os.path.join(root, folder, "Cover", ".ignore"), 'w').close()
            if not os.path.exists(os.path.join(root, folder, "Cover", id + "b.png")):
                if banner:
                    bannerimg = scrape(banner)
                    with open(os.path.join(root, folder, "Cover", id + "b.png"), 'wb') as f:
                        bannerimg.decode_content = True
                        f.write(bannerimg.content)
            if not os.path.exists(os.path.join(root, folder, "Cover", id + "c.png")):
                coverimg = scrape(cover)
                with open(os.path.join(root, folder, "Cover", id + "c.png"), 'wb') as f:
                    coverimg.decode_content = True
                    f.write(coverimg.content)
            cover_folder(os.path.join(root, folder, "Cover", id + "c.png"), os.path.join(root, folder), title)

        tmp = dict()
        limits = dict()
        shift_val = dict()
        missings = dict()
        for ext in related_exts:
            tmp[ext] = []
            limits[ext] = {'min': math.inf, 'max': 0, 'digits': 0}
            shift_val[ext] = 0
            missings[ext] = []
            files = [file for file in files if os.path.splitext(file)[1] in related_exts]
        files.sort(key=lambda x: natsort.natsort_key(str(int(extract_episode_number(x, os.path.basename(dir) if match_id is None else os.path.basename(dir)[len(match_id):])[1].split('-')[0]))))
        for file in files:
            ext = os.path.splitext(file)[1]
            tmp[ext].append(file)
            n = list(map(int, extract_episode_number(file, os.path.basename(dir) if match_id is None else os.path.basename(dir)[len(match_id):])[1].split('-')))
            for num in n:
                if num > limits[ext]['max']:
                    limits[ext]['max'] = num
                    limits[ext]['digits'] = len(str(num))
                if num < limits[ext]['min']:
                    limits[ext]['min'] = num
        files = tmp
        for ext, v in files.items():
            if len(v) == 0:
                continue
            if limits[ext]['max'] - limits[ext]['min'] + 1 > len(v):
                missing = limits[ext]['min']
                for file in v:
                    n = list(map(int, extract_episode_number(file, os.path.basename(dir) if match_id is None else os.path.basename(dir)[len(match_id):])[1].split('-')))
                    for num in n:
                        while missing != num:
                            missings[ext].append(missing)
                            missing += 1
                        missing += 1
                logger_module.warning('"%s" : Missing "*%s" found at %s!', title, ext, str(list(map(lambda num: num - (shift_val[ext] if shift else 0), missings[ext]))))

        for ext, v in files.items():
            for file in v:
                if (shift and shift_val[ext] != 0) or not ep_follows_template(file, title, ext, lang, digits=limits[ext]['digits']):
                    episode = list(map(int, extract_episode_number(file, os.path.basename(dir) if match_id is None else os.path.basename(dir)[len(match_id):], log=True)[1].split('-')))
                    for i in range(len(episode)):
                        if shift:
                            episode[i] = str(episode[i] - shift_val[ext])
                        episode[i] = '0'*(limits[ext]['digits'] - len(str(episode[i]))) + str(episode[i])
                    episode = '-'.join(episode)
                    os.rename(os.path.join(root, folder, file), os.path.join(root, folder, ep_filename(title, episode, ext, lang)))
    logger_module.info('Finished tidying library.')


def create_watching_dir(uid='None', root='.', lang=Lang.NATIVE):
    logger_module.info("Creating current season's folders with lang=%s...", lang)

    if os.path.exists('response.json'):
        logger_module.debug('"response.json" found! Using local data.')
        with open('response.json', 'r', encoding='utf-8') as f:
            medias = json.load(f)
    else:
        logger_module.debug('No "response.json" found. Requesting from API...')
        medias = anilist_api.get_current_anime(uid=uid, dump=True)
    for media in medias:
        id = str(media['id'])
        if lang is Lang.NATIVE:
            title = special_chars(media['title']['native'] if media['title']['native'] is not None else media['title']['romaji'], replace=True)
        elif lang is Lang.ROMAJI:
            title = special_chars(media['title']['romaji'], replace=False)
        elif lang is Lang.ENGLISH:
            title = special_chars(media['title']['english'] if media['title']['english'] is not None else media['title']['romaji'], replace=False)
        folder = title
        logger_module.info('Processing "%s"', title)
        if os.path.exists(os.path.join(root, folder)):
            temp = next(filter(lambda x: regex.match(r'^\d+$', x) is not None, next(walklevel(os.path.join(root, folder), depth=1))[2]), None)
            if temp is None:
                logger_module.warning('Unknown folder "%s" exists! Please remove.', folder)
                continue
            elif temp == id:
                logger_module.debug('Using "%s" for IO operations.', folder)
                if os.path.exists(os.path.join(root, folder, "desktop.ini")):
                    continue
            else:
                folder = f'[{id}] {title}'
                logger_module.debug('Using "%s" for IO operations.', folder)
                if os.path.exists(os.path.join(root, folder, "desktop.ini")):
                    continue
        banner = media['bannerImage']
        cover = media["coverImage"]["extraLarge"]
        if not os.path.exists(os.path.join(root, folder)):
            os.mkdir(os.path.join(root, folder))
        if not os.path.exists(os.path.join(root, folder, id)):
            open(os.path.join(root, folder, id), 'w').close()
        if not os.path.exists(os.path.join(root, folder, "Cover")):
            os.mkdir(os.path.join(root, folder, "Cover"))
            open(os.path.join(root, folder, "Cover", ".ignore"), 'w').close()
        if not os.path.exists(os.path.join(root, folder, "Cover", id + "b.png")):
            if banner:
                bannerimg = scrape(banner)
                with open(os.path.join(root, folder, "Cover", id + "b.png"), 'wb') as f:
                    bannerimg.decode_content = True
                    f.write(bannerimg.content)
        if not os.path.exists(os.path.join(root, folder, "Cover", id + "c.png")):
            coverimg = scrape(cover)
            with open(os.path.join(root, folder, "Cover", id + "c.png"), 'wb') as f:
                coverimg.decode_content = True
                f.write(coverimg.content)
        cover_folder(os.path.join(root, folder, "Cover", id + "c.png"), os.path.join(root, folder), title)
    logger_module.info("Finished creating current season's folders.")


def update_rss(category, uid='None', lang=Lang.NATIVE):
    logger_module.info('Updating RSS with lang=%s...', lang)
    root = os.path.join(os.getenv('APPDATA'), 'qBittorrent')
    with open(os.path.join(root, 'categories.json'), 'r', encoding='utf-8') as f:
        save_loc = json.load(f)[category]['save_path']
    root = os.path.join(root, 'rss')
    group = 'Anime Manager'
    create_watching_dir(uid=uid, root=save_loc, lang=lang)
    with open('response.json', 'r', encoding='utf-8') as f:
        medias = json.load(f)
    with open(os.path.join(root, 'feeds.json'), 'r', encoding='utf-8') as f:
        feeds = json.load(f)
    with open(os.path.join(root, 'download_rules.json'), 'r', encoding='utf-8') as f:
        dl_rules = json.load(f)
    if group not in feeds.keys():
        feed_group = {}
    else:
        feed_group = feeds['Anime Manager']
    ids = [str(media['id']) for media in medias]
    if lang is Lang.NATIVE:
        titles = [media['title']['native'] if media['title']['native'] is not None else media['title']['romaji'] for media in medias]
    elif lang is Lang.ROMAJI:
        titles = [media['title']['romaji'] for media in medias]
    elif lang is Lang.ENGLISH:
        titles = [media['title']['english'] if media['title']['english'] is not None else media['title']['romaji'] for media in medias]
    covers = [os.path.join(save_loc, titles[i], 'Cover', str(ids[i]) + 'c.png') for i in range(len(ids))]
    links = [''] * len(ids)
    for k, v in list(feed_group.items()):
        try:
            i = ids.index(k)
            links[i] = v['url']
        except ValueError:
            logger_module.warning('Deleting RSS for [%s]', k)
            del feed_group[k]
            del dl_rules[k]
    links = app.run(ids, titles, covers, links)
    if links is None:
        logger_module.error('Canceled by user.')
        return
    for i in range(len(ids)):
        if links[i] == '':
            continue
        if ids[i] not in feed_group.keys():
            logger_module.warning('Creating RSS for "[%s] %s"', ids[i], titles[i])
            feed_group[ids[i]] = {}
            dl_rules[ids[i]] = {'addPaused': True,
                                'affectedFeeds': None,
                                'assignedCategory': 'Weekly',
                                'enabled': True,
                                'episodeFilter': '',
                                'ignoreDays': 0,
                                'lastMatch': None,
                                'mustContain': '',
                                'mustNotContain': '',
                                'previouslyMatchedEpisodes': [],
                                'savePath': '',
                                'smartFilter': False,
                                'torrentContentLayout': None,
                                'useRegex': False
                                }
        else:
            logger_module.debug('Updating RSS for "[%s] %s"', ids[i], titles[i])
        dl_rules[ids[i]]['savePath'] = os.path.join(save_loc, titles[i])
        dl_rules[ids[i]]['affectedFeeds'] = [links[i]]
        feed_group[ids[i]]['url'] = links[i]
    feeds[group] = feed_group

    logger_module.info('Backing "feeds.json" and "download_rules.json" up...')
    backup(os.path.join(root, 'feeds.json'), '.')
    backup(os.path.join(root, 'download_rules.json'), '.')
    logger_module.info('Writing "feeds.json" and "download_rules.json"...')
    with open(os.path.join(root, 'feeds.json'), 'w', encoding='utf-8') as f:
        json.dump(feeds, f, ensure_ascii=False, indent=4)
    with open(os.path.join(root, 'download_rules.json'), 'w', encoding='utf-8') as f:
        json.dump(dl_rules, f, ensure_ascii=False, indent=4)
    logger_module.info('Finished updating RSS.')


def tidy_episodes(uid='None', files=None, root='.', lang=Lang.NATIVE, shift=False):
    logger_module.info('Tidying episodes...')
    if os.path.exists('response.json'):
        logger_module.info('"response.json" found! Using local data.')
        with open('response.json', 'r', encoding='utf-8') as f:
            medias = json.load(f)
    else:
        logger_module.info('No "response.json" found. Requesting from API...')
        medias = anilist_api.get_current_anime(uid=uid, dump=True)
    ntv = []
    rmj = []
    eng = []
    synonymss = []
    for media in medias:
        ntv.append(media['title']['native'])
        rmj.append(media['title']['romaji'])
        eng.append(media['title']['english'])
        synonymss.append(media['synonyms'])
    all = list(ntv)
    all.extend(rmj)
    all.extend(eng)
    for synonyms in synonymss:
        all.extend(synonyms)
    if files is None:
        walk = next(os.walk(root))
        files = [file for file in walk[2] if os.path.splitext(file)[1] in related_exts]
        #TODO include folders in other languages
        if lang == Lang.NATIVE:
            folders = [folder for folder in walk[1] if folder in ntv]
        elif lang == Lang.ROMAJI:
            folders = [folder for folder in walk[1] if folder in rmj]
        elif lang == Lang.ENGLISH:
            folders = [folder for folder in walk[1] if folder in eng]
        ffiles = [[file for file in next(os.walk(os.path.join(root, folder)))[2] if os.path.splitext(file)[1] in related_exts] for folder in folders]
        roots = [root] * len(files)
    else:
        folders = None
        roots = [os.path.dirname(file) for file in files]
        files = [os.path.basename(file) for file in files]
    if len(files) != 0:
        seasons, episodes, files_edited = zip(*list(map(lambda file: extract_episode_number(file, log=True), files)))
        dist = process.cdist(queries=all, choices=files_edited, processor=str.lower, scorer=fuzz.token_ratio)
        indices = dist.argmax(axis=0)
        # DEBUG
        # titles = map(all.__getitem__, indices)
        # done = list(zip(files_edited, titles))

        for i in range(len(indices)):
            ln = len(all)
            for j in reversed(range(len(synonymss))):
                ln -= len(synonymss[j])
                if ln <= indices[i]:
                    break
            else:
                j = indices[i] % len(ntv)
            indices[i] = j
    if lang == Lang.NATIVE:
        get_title = lambda i: special_chars(ntv[i], replace=True)
    elif lang == Lang.ROMAJI:
        get_title = lambda i: special_chars(rmj[i], replace=False)
    elif lang == Lang.ENGLISH:
        get_title = lambda i: special_chars(eng[i], replace=False)

    if folders is not None:
        for folder, ffile in zip(folders, ffiles):
            logger_module.info('Processing "%s"', folder)
            tmp = dict()
            limits = dict()
            shift_val = dict()
            missings = dict()
            for ext in related_exts:
                tmp[ext] = []
                limits[ext] = {'min': math.inf, 'max': 0, 'digits': 0}
                shift_val[ext] = 0
                missings[ext] = []
            ffile.sort(key=lambda x: natsort.natsort_key(str(int(extract_episode_number(x, folder)[1].split('-')[0]))))
            for file in ffile:
                ext = os.path.splitext(file)[1]
                if ext in related_exts:
                    tmp[ext].append(file)
                    n = list(map(int, extract_episode_number(file, folder)[1].split('-')))
                    for num in n:
                        if num > limits[ext]['max']:
                            limits[ext]['max'] = num
                            limits[ext]['digits'] = len(str(num))
                        if num < limits[ext]['min']:
                            limits[ext]['min'] = num
            ffile = tmp
            for ext, v in ffile.items():
                if len(v) == 0:
                    continue
                if limits[ext]['max'] - limits[ext]['min'] + 1 > len(v):
                    missing = limits[ext]['min']
                    for file in v:
                        n = list(map(int, extract_episode_number(file, folder)[1].split('-')))
                        for num in n:
                            while missing != num:
                                missings[ext].append(missing)
                                missing += 1
                            missing += 1
                    logger_module.warning('"%s" : missing "*%s" found at %s!', folder, ext, str(list(map(lambda num: num - (shift_val[ext] if shift else 0), missings[ext]))))

            for ext, v in ffile.items():
                for file in v:
                    if (shift and shift_val[ext] != 0) or not ep_follows_template(file, folder, ext, lang, digits=limits[ext]['digits']):
                        episode = list(map(int, extract_episode_number(file, folder, log=True)[1].split('-')))
                        for i in range(len(episode)):
                            if shift:
                                episode[i] = str(episode[i] - shift_val[ext])
                            episode[i] = '0'*(limits[ext]['digits'] - len(str(episode[i]))) + str(episode[0])
                        episode = '-'.join(episode)
                        os.rename(os.path.join(root, folder, file), os.path.join(root, folder, ep_filename(folder, episode, ext, lang)))

    if len(files) != 0:
        for root, file, episode, index in zip(roots, files, episodes, indices):
            title = get_title(index)
            ext = os.path.splitext(file)[1]
            os.rename(os.path.join(root, file), os.path.join(root, ep_filename(title, episode, ext, lang)))
    logger_module.info('Finished tidying episodes.')


def update_tsumi(customlist, auth=None, root='.'):
    logger_module.info('Updating on-hand library to "%s" list...', customlist)
    if not anilist_api.is_authorized():
        if auth is not None:
            anilist_api.set_auth(auth)
            if not anilist_api.is_authorized():
                logger_module.error('Login failed! Aborting...')
                return
        else:
            logger_module.error('Not authorized! Aborting...')
            return
    walkie = walklevel(root, depth=1)
    next(walkie)
    ids = dict()
    complets = dict()
    logger_module.info('Collecting anime ids...')
    for _, _, files in walkie:
        id = next(filter(lambda x: regex.match(r'^\d+$', x) is not None, files), None)
        if id is not None:
            ids[int(id)] = 0
    logger_module.info('Requesting anime list entries...')
    entries = anilist_api.get_anime_entires(list(ids.keys()))
    for entry in entries:
        if (entry['status'] != 'PLANNING' and entry['status'] != 'PAUSED') and entry['customLists'][customlist]:
            del ids[entry['mediaId']]
            complets[entry['mediaId']] = [entry['id'], [k for k, v in entry['customLists'].items() if k != customlist and v]]
        elif (entry['status'] != 'PLANNING' and entry['status'] != 'PAUSED') or entry['customLists'][customlist]:
            del ids[entry['mediaId']]
        else:
            ids[entry['mediaId']] = [entry['id'], [k for k, v in entry['customLists'].items() if k == customlist or v]]
    logger_module.info('Removing completed anime from list...')
    for mediaId, v in complets.items():
        success = anilist_api.add_anime_to_customlists(v[0], v[1])
        if not success:
            logger_module.error('Updating on-hand library to "%s" list failed!', customlist)
            return
    logger_module.info('Adding on-hand anime to list...')
    for mediaId, v in ids.items():
        if v == 0:
            success = anilist_api.add_anime_to_customlists(mediaId, [customlist], is_mediaId=True)
            if not success:
                logger_module.error('Updating on-hand library to "%s" list failed!', customlist)
                return
        else:
            success = anilist_api.add_anime_to_customlists(v[0], v[1])
            if not success:
                logger_module.error('Updating on-hand library to "%s" list failed!', customlist)
                return
    logger_module.info('Finished adding library to "%s" list.', customlist)

# List of problems:
# 1 season 2 cours listed as s1 s2
# 2 seasons special chars difference (kaguya)
# 2 seasons second has 2, 2nd season, second season
# 2 seasons same name (hanako-kun)
# 2 seasons different names listed as same s1 s2
