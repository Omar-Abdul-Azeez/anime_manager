import logging

logger_anilist = logging.getLogger(__name__)
logger_anilist.addHandler(logging.NullHandler())

from anime import network
from anime.enums import Lang


endpoint = 'https://graphql.anilist.co'
check_login = """
              query {
                Viewer {
                  id
                  name
                }
              }"""
query_anime = """
              query($page: Int, $search: String, $id: Int, $ids: [Int]) {
                Page(page: $page, perPage: 50) {
                  pageInfo {
                  hasNextPage
                  }
                  media(search: $search, id: $id, id_in: $ids, type: ANIME) {
                    id
                    title {
                      romaji
                      english
                      native
                    }
                    synonyms
                    bannerImage
                    coverImage {
                      extraLarge
                    }
                    nextAiringEpisode {
                      episode
                      airingAt
                    }
                  }
                }
              }
              """
query_current = """
                query($uid: Int) {
                  MediaListCollection(userId: $uid, status: CURRENT, type: ANIME) {
                    lists {
                      name
                      isCustomList
                      isSplitCompletedList
                      status
                      entries {
                        media {
                          id
                          status
                          title {
                            romaji
                            english
                            native
                            userPreferred
                          }
                          synonyms
                          bannerImage
                          coverImage {
                            extraLarge
                          }
                          nextAiringEpisode {
                            episode
                            airingAt
                          }
                        }
                      }
                    }
                  }
                }
                """
query_anime_entries = """
                   query($page: Int, $uid: Int, $id: Int, $ids: [Int]) {
                     Page(page: $page, perPage: 50) {
                       pageInfo {
                       hasNextPage
                       }
                       mediaList(userId: $uid, mediaId: $id, mediaId_in: $ids, type: ANIME) {
                         id
                         mediaId
                         status
                         customLists
                       }
                     }
                   }"""
mutate_anime_entry = """
                 mutation($id: Int, $mediaId: Int, $status: MediaListStatus, $customLists: [String]) {
                   SaveMediaListEntry(id: $id, mediaId: $mediaId, status: $status, customLists: $customLists) {
                   id
                   mediaId
                   customLists
                   }
                 }"""


def ask(msg, choices, index=False, show=False, default=None, limit=0, none=False):
    while True:
        print(msg)
        if show:
            for i in range(len(choices)):
                if limit != 0 and i != 0 and i % limit == 0:
                    ans = input('>')
                    if ans != '':
                        if ans in choices:
                            if index:
                                return choices.index(ans)
                            else:
                                return ans
                        ans = int(ans) - 1
                        if -1 < ans < i:
                            if index:
                                return ans
                            else:
                                return choices[ans]
                    print(msg)
                print(f'{i + 1})  {choices[i]}')
            if none:
                print(f'{i + 2})  None')
        ans = input('>')
        if ans == '' and show:
            return default
        if ans in choices:
            if index:
                return choices.index(ans)
            else:
                return ans

        if show:
            ans = int(ans) - 1
            if ans == len(choices) and none:
                return None
            elif -1 < ans < len(choices):
                if index:
                    return ans
                else:
                    return choices[ans]


def check_api_limit(limit, perTime):
    from time import sleep
    count = 0
    while True:
        if count == limit:
            logger_anilist.info('API limit reached. Waiting for %d seconds...', perTime)
            sleep(perTime)
            count = 0
            logger_anilist.info('Finished Waiting.')
        count += 1
        yield count


API_limit = check_api_limit(limit=90, perTime=65)
headers = None
user = 'None'


def request(query, headers_l=None, variables=None):
    next(API_limit)
    if headers_l is None:
        if headers is None:
            response = network.request(endpoint, json={'query': query, 'variables': variables})
        else:
            response = network.request(endpoint, headers=headers, json={'query': query, 'variables': variables})
    else:
        response = network.request(endpoint, headers=headers_l, json={'query': query, 'variables': variables})
    if "errors" in response.keys():
        for err in response["errors"]:
            logger_anilist.error('API response NOT OK! Status code = %d  "%s" %s', err["status"], err["message"], str(err['locations'][0]))
        return None
    logger_anilist.debug('API response OK!')
    return response["data"]


def get_auth():
    network.open('https://anilist.co/api/v2/oauth/authorize?client_id=14129&response_type=token')


def set_auth(auth):
    global headers, user
    tmp = {'Authorization': 'Bearer ' + auth,
               'Content-Type': 'application/json',
               'Accept': 'application/json'}
    result = request(check_login, headers_l=tmp)
    if result is None:
        return False
    headers = tmp
    user = result['Viewer']['id']
    return True


def is_authorized():
    return headers is not None


def get_current_anime(uid='None', dump=False):
    if uid == 'None':
        uid = user
    variables = {'uid': uid}
    next(API_limit)
    response = request(query_current, variables)
    response = response['MediaListCollection']['lists'][0]['entries']
    medias = [entry['media'] for entry in response if entry['media']['status'] == 'RELEASING']
    if dump:
        import json
        with open('response.json', 'w', encoding='utf-8') as f:
            json.dump(medias, f, ensure_ascii=False)
    return medias


def get_anime(search=None, ids=None, auto=True, lang=Lang.NATIVE, dump=False):
    page = 1
    variables = {'page': page}
    if ids is not None:
        if isinstance(ids, int):
            variables['id'] = ids

            response = request(query_anime, variables)
            media = response["Page"]["media"][0]
        else:
            variables['ids'] = ids

            response = request(query_anime, variables)
            hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
            media = response["Page"]["media"]
            while hasNextPage:
                page += 1
                variables['page'] = page
                response = request(query_anime, variables)
                hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
                media.extend(response["Page"]["media"])
    elif search is not None:
        variables['search'] = search

        response = request(query_anime, variables)
        if auto:
            media = response["Page"]["media"][0]
        else:
            hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
            medias = response["Page"]["media"]
            mediass = []
            ans = ask(search + ' :', [media['title'][str(lang)] for media in medias], index=True, show=True, limit=10)
            while ans is None:
                if hasNextPage:
                    mediass.append(medias)
                    page += 1
                    variables['page'] = page
                    response = request(query_anime, variables)
                    hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
                    medias = response["Page"]["media"]
                    ans = ask(search + ' :', [media['title'][str(lang)] for media in medias], index=True, show=True, limit=10)
                else:
                    if len(medias) != 0:
                        mediass.append(medias)
                        medias = []
                    ans = ask(search + ' :', [media['title'][str(lang)] for medias in mediass for media in medias], index=True, show=True, limit=10)
            # when last page is reached this becomes true
            # len(mediass) = page - 1 except for the last page
            if page > len(mediass):
                media = medias[ans]
            else:
                media = mediass[int(ans / len(mediass[0]))][ans % len(mediass[0])]

    if dump:
        import json
        with open('response.json', 'w', encoding='utf-8') as f:
            json.dump(media, f, ensure_ascii=False)
    return media


def get_anime_entires(ids, uid='None', dump=False):
    if uid == 'None':
        uid = user
    page = 1
    variables = {'page': page, 'uid': uid}
    if isinstance(ids, int):
        variables['id'] = ids

        response = request(query_anime_entries, variables)
        media = response["Page"]["mediaList"][0]
    else:
        variables['ids'] = ids

        response = request(query_anime_entries, variables)
        hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
        media = response["Page"]["mediaList"]
        while hasNextPage:
            page += 1
            variables['page'] = page
            response = request(query_anime_entries, variables)
            hasNextPage = response["Page"]["pageInfo"]["hasNextPage"]
            media.extend(response["Page"]["mediaList"])

    if dump:
        import json
        with open('response.json', 'w', encoding='utf-8') as f:
            json.dump(media, f, ensure_ascii=False)
    return media


def add_anime_to_customlists(id, customlists, is_mediaId=False):
    if is_mediaId:
        variables = {'mediaId': id, 'status': 'PLANNING', 'customLists': customlists}
    else:
        variables = {'id': id, 'customLists': customlists}
    result = request(mutate_anime_entry, variables)
    if result is None:
        return False
    else:
        return True
