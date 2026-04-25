try:
    from ._native import compress, decompress
except ImportError:
    print("WARNING: using native-python LZ77, operations will be slow")
    from ._lz77_py import compress, decompress

__all__ = ["compress", "decompress"]
