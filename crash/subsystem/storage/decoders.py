# -*- coding: utf-8 -*-
# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:

import gdb
from typing import Union, List
from crash.infra.lookup import SymbolCallback

EndIOSpecifier = Union[int, str, List[str], gdb.Value, gdb.Symbol, None]

decoders = {}

class Decoder(object):

    __endio__: EndIOSpecifier = None

    def __init__(self):
        self.interpreted = False

    def interpret(self) -> None:
        pass

    def __getattr__(self, name):
        if self.interpreted:
            raise AttributeError(f"No such attribute `{name}'")

        self.interpret()
        self.interpreted = True
        return getattr(self, name)

    @classmethod
    def register(cls):
        register_decoder(cls.__endio__, cls)

    def __str__(self) -> str:
        pass

    def __next__(self):
        return None


class DecodeBufferHead(Decoder):
    """
    Decodes a struct buffer_head

    This method decodes a generic struct buffer_head, when no
    implementation-specific decoder is available

    Args:
        bio(gdb.Value<struct buffer_head>): The struct buffer_head to be
            decoded.
    """

    description = "{:x} buffer_head: for dev {}, block {}, size {} (undecoded)"

    def __init__(self, bh: gdb.Value):
        super().__init__()
        self.bh = bh

    def interpret(self):
        pass

    def __str__(self):
        return self.description.format(int(self.bh),
                                       block_device_name(self.bh['b_bdev']),
                                       self.bh['b_blocknr'], self.bh['b_size'])

def register_decoder(endio: EndIOSpecifier, decoder: Decoder) -> None:
    """
    Registers a bio/buffer_head decoder with the storage subsystem.

    A decoder is a class that accepts a bio, buffer_head, or other object,
    potentially interprets the private members of the object, and
    returns a Decoder object that describes it.

    The only mandatory part of a Decoder is the __str__ method to
    print the description.

    If the bio is part of a stack, the __next__ method will contain
    the next Decoder object in the stack.  It does not necessarily need
    to be a bio.  The Decoder does not need to be registered unless it
    will be a top-level decoder.

    Other attributes can be added as-needed to allow informed callers
    to obtain direct information.

    Args:
        endio (str, list of str, gdb.Symbol, gdb.Value, or int): The function
            used as an endio callback.

            The str or list of str arguments are used to register a callback
            such that the Decoder is registered when the symbol is available.

            The gdb.Symbol, gdb.Value, and int versions are to be used
            once the symbol is available for resolution.

            If in doubt, use the names instead of the symbols objects.

        decoder (Decoder): The decoder class used to handle this object.

    """
    debug = False
    if isinstance(endio, str):
        if debug:
            print(f"Registering {endio} as callback")
        x = SymbolCallback(endio, lambda a: register_decoder(a, decoder))
        return
    elif isinstance(endio, list) and isinstance(endio[0], str):
        for sym in endio:
            if debug:
                print(f"Registering {sym} as callback")
            x = SymbolCallback(sym, lambda a: register_decoder(a, decoder))
        return

    if isinstance(endio, gdb.Symbol):
        endio = endio.value()

    if isinstance(endio, gdb.Value):
        endio = int(endio.address)

    if debug:
        print(f"Registering {endio:#x} for real")

    decoders[endio] = decoder

class GenericBioDecoder(Decoder):
    description = "{:x} bio: undecoded bio on {} ({})"
    def __init__(self, bio):
        super().__init__()
        self.bio = bio

    def __str__(self):
        return self.description.format(int(self.bio),
                                       block_device_name(self.bio['bi_bdev']),
                                       bio['bi_end_io'])

def decode_bio(bio: gdb.Value) -> Decoder:
    """
    Decodes a single bio, if possible

    This method will return a Decoder object describing a single bio
    after decoding it using a registered decoder, if available.

    If no decoder is registered, a generic description will be used.

    Args:
        bio (gdb.Value<struct bio>): The bio to decode
    """

    try:
        return decoders[int(bio['bi_end_io'])](bio)
    except KeyError:
        return GenericBioDecoder(bio)

def decode_bh(bh: gdb.Value) -> Decoder:
    try:
        return decoders[int(bh['b_endio'])](bh)
    except KeyError:
        return DecodeBufferHead(bh)
