from pathlib import Path

from setuptools import Extension, setup


def _extension():
    import pybind11

    return Extension(
        'rolling_features_native',
        [str(Path('src') / 'rolling_features.cpp')],
        include_dirs=[pybind11.get_include()],
        language='c++',
        extra_compile_args=['-O3', '-std=c++17'],
    )


setup(
    name='rolling-features-native',
    version='0.1.0',
    description='Optional native rolling feature kernels for the data science control plane',
    ext_modules=[_extension()],
)

