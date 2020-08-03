import bisect
from collections.abc import MutableMapping
from functools import reduce
from operator import or_

arabic_table = (
    (0x0600, 0x061e),
    (0x0620, 0x06ff),
    (0x0750, 0x077f),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
    (0x10E60, 0x10E7F),
    (0x1EC70, 0x1ECBF),
    (0x1ED00, 0x1ED4F),
    (0x1EE00, 0x1EEFF)
)
arabic_table_flatten = []
for x, y in arabic_table:
    arabic_table_flatten.extend([x, y + 1])


def is_arabic(sentence):
    def is_arabic_char(char):
        return bool(bisect.bisect(arabic_table_flatten, ord(char)) % 2)

    return reduce(or_, map(is_arabic_char, sentence))


class MaxSizeDict(MutableMapping):
    def __init__(self, maxlen, *a, **k):
        self.maxlen = maxlen
        self.d = dict(*a, **k)
        while len(self) > maxlen:
            self.popitem()

    def __iter__(self):
        return iter(self.d)

    def __len__(self):
        return len(self.d)

    def __getitem__(self, k):
        return self.d[k]

    def __delitem__(self, k):
        del self.d[k]

    def __setitem__(self, k, v):
        if k not in self and len(self) == self.maxlen:
            self.popitem()
        self.d[k] = v

    def __repr__(self):
        return repr(self.d)
