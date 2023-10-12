# -*- encoding:utf-8 -*-
from enum import Enum


class Lang(Enum):
    NATIVE = 'native'
    ROMAJI = 'romaji'
    ENGLISH = 'english'

    def __str__(self):
        return self.value
