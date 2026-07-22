"""Stable content fingerprints shared by lineage and persistent snapshots."""

import hashlib

import pandas as pd


def fingerprint_dataset(data: pd.DataFrame) -> str:
    """Return a SHA-256 identity for dataframe values, labels, and dtypes.

    The function deliberately includes the index because it identifies rows in
    many transformed datasets.  Keeping this helper outside either repository
    or persistence implementation guarantees that an in-session lineage
    revision and its reusable on-disk snapshot use the same identity.
    """
    # [impl->req~ring5.data.dataset-snapshots~1]
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Dataset fingerprints require a pandas DataFrame.")
    digest = hashlib.sha256()
    digest.update(repr(tuple(data.columns)).encode("utf-8"))
    digest.update(repr(tuple(data.columns.names)).encode("utf-8"))
    digest.update(repr(tuple(str(dtype) for dtype in data.dtypes)).encode("utf-8"))
    digest.update(repr(tuple(data.index.names)).encode("utf-8"))
    index_dtypes = (
        tuple(str(data.index.get_level_values(level).dtype) for level in range(data.index.nlevels))
        if isinstance(data.index, pd.MultiIndex)
        else (str(data.index.dtype),)
    )
    digest.update(repr(index_dtypes).encode("utf-8"))
    try:
        hashes = pd.util.hash_pandas_object(data, index=True, categorize=True)
        digest.update(hashes.to_numpy(copy=False).tobytes())
    except (TypeError, ValueError):
        digest.update(data.to_csv(index=True).encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"
