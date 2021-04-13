"""
attrdict contains several mapping objects that allow access to their
keys as attributes.
"""
from cryptostore.attrdict.mapping import AttrMap
from cryptostore.attrdict.dictionary import AttrDict
from cryptostore.attrdict.default import AttrDefault


__all__ = ['AttrMap', 'AttrDict', 'AttrDefault']
