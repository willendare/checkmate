# This code is part of the checkmate project.
# Copyright (C) 2014-2015 The checkmate project contributors
# 
# This program is free software under the terms of the GNU GPL, either
# version 3 of the License, or (at your option) any later version.

import collections


class ValidationDict(object):
    def __init__(self):
        super().__init__()
        self.collected_items = collections.defaultdict(list)
        self.validated_items = collections.defaultdict(list)

    def record(self, block, item_list):
        self.collected_items[block].extend(item_list)
        self.validated_items[block].extend(item_list)

    def check(self, block):
        try:
            self.collected_items[block].pop()
            return True
        except IndexError:
            return False

    def clear(self):
        self.collected_items.clear()
        self.validated_items.clear()
