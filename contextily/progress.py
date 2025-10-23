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
        A tqdm-compatible progress bar class. If None, progress bar is disabled.
        The progress bar class should have the same interface as tqdm.
        Common alternatives include:
        - tqdm.notebook.tqdm for Jupyter notebooks
        - custom implementations with the same interface
    """
    global _progress_bar
    _progress_bar = progress_bar


def get_progress_bar():
    """
    Returns the progress bar class to be used for downloading tiles.
    If progress bars are disabled (set to None), returns a no-op context
    manager that doesn't display progress.

    Returns
    ----------
    progress_bar : callable
        A callable that returns either a tqdm-compatible progress bar or a
        no-op context manager with update/close methods if progress bars
        are disabled.
    """
    if _progress_bar is None:
        class NoOpProgress:
            def __init__(self, *args, **kwargs):
                self.context = nullcontext()
                
            def __enter__(self):
                self.context.__enter__()
                return self
                
            def __exit__(self, *args):
                self.context.__exit__(*args)
                
            def update(self, n=1):
                pass
                
            def close(self):
                pass
                
        return lambda *args, **kwargs: NoOpProgress(*args, **kwargs)
    return _progress_bar
