from setuptools import setup, Extension

setup(
    ext_modules=[
        Extension("reven.fast.pattern", sources=["src/reven/fast/pattern.c"]),
        Extension("reven.fast.ngram", sources=["src/reven/fast/ngram.c"]),
    ]
)
