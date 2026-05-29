"""HerediCalc — Full Likelihood Bayes factor for cosegregation analysis."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("heredicalc")
except PackageNotFoundError:
    __version__ = "dev"
