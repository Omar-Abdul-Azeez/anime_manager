# -*- encoding:utf-8 -*-
related_exts = {'.mkv', '.mp4', '.avi', '.wmv', '.mks', '.srt', '.ass', '.sup'}
pattern_id = r'(\[\d+] )'
pattern_se = r'(?<=' \
                  r'[. x_-]?( - |_-_)?(?>' \
                                        r'(?>' \
                                            r'(2nd[. x_-]?season)|' \
                                            r'((?>season|s)[. x_-]?)(?<!\d)(\d+([.-]\d+)*)(?!\d)|' \
                                            r'(第)?(?<!\d)(\d+([.-]\d+)*)(?!\d)(期)' \
                                        r')[. x_-]?(?: - |_-_)?' \
                                    r')?' \
             r')((?>episode|ep|e)[. x_-]?)?(第)?(?<!\d)(\d+([.-]\d+)*)(?!\d)(話)?'
pattern_se_groups = lambda match: ('2' if match[1] is not None else match[3] if match[3] is not None else match[6], match[11])
pattern_ex = '(?:' \
                 '\\' + '$|\\'.join(related_exts) + r'$|' \
                r'\[.*?]|' \
                r'\(dual[. _-]audio\)|' \
                r'[. _-]\d+(?:p|bit)|' \
                r'\d+(?:p|bit)[. _-]|' \
                r'[. _-]\(?(?:' \
                             r'web(?:\-?dl)?|amzn|amazon|disney|dsnp|' \
                             r'aac|ac3|ddp(?:[. _]?2.0)?|hevc|(h\.|x)26[45]\-?varyg|\w+?[_-]?raws' \
                         r')\)?|' \
                r'\(?(?:' \
                       r'web(?:\-?dl)?|amzn|amazon|disney|dsnp|' \
                       r'aac|ac3|ddp(?:[. _]?2.0)?|hevc|(h\.|x)26[45]|-?varyg|\w+?[_-]?raws' \
                   r')\)?[. _-]|' \
                r'[. _-]\([^\(\)]*(?:' \
                                    r'web(?:\-?dl)|amzn|amazon|disney|dsnp|' \
                                    r'aac|ac3|ddp(?:[. _]?2.0)?|hevc|(h\.|x)26[45]|-?varyg|\w+?[_-]?raws' \
                                r')[^\(\)]*\)|' \
                r'\([^\(\)]*(?:' \
                              r'web(?:\-?dl)|amzn|amazon|disney|dsnp|' \
                              r'aac|ac3|ddp(?:[. _]?2.0)?|hevc|(h\.|x)26[45]|-?varyg|\w+?[_-]?raws' \
                          r')[^\(\)]*\)[. _-]' \
            r')'


def ep_filename(title, episode, ext, lang):
    from anime.enums import Lang
    if lang is Lang.NATIVE:
        return title + ' ' + '第' + episode + '話' + ext
    elif lang is Lang.ROMAJI:
        return title + ' ' + 'EP' + episode + ext
    elif lang is Lang.ENGLISH:
        return title + ' ' + 'EP' + episode + ext
