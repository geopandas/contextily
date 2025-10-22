from tqdm import tqdm as _default_progress_bar
from contextlib import nullcontext

# Default progress bar class (can be changed by set_progress_bar)
_progress_bar = _default_progress_bar

def set_progress_bar(progress_bar=None):
    """
    Set the progress bar class to be used for downloading tiles.

    Parameters
    ----------
    progress_bar : class, optional
        A tqdm-compatible progress bar class. If None, uses the default tqdm.
        The progress bar class should have the same interface as tqdm.
        Common alternatives include:
        - tqdm.notebook.tqdm for Jupyter notebooks
        - custom implementations with the same interface
    """
    global _progress_bar
    _progress_bar = progress_bar if progress_bar is not None else _default_progress_bar


def get_progress_bar():
    """
    Returns the progress bar class to be used for downloading tiles.

    Returns
    ----------
    progress_bar : class
        A tqdm-compatible progress bar class.
    """
    return _progress_bar
