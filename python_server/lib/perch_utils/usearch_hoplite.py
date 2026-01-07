import sqlite3
from typing import Any
from perch_hoplite.db import sqlite_usearch_impl
from ml_collections import config_dict
import numpy as np
from usearch import index as uindex
from etils import epath


class SQLiteUsearchDBExt(sqlite_usearch_impl.SQLiteUSearchDB):
    """
    Extension of usearch hoplite db to add additional functionality.
    """

    def __init__(
        self,
        db_path: str,
        db: sqlite3.Connection,
        ui: uindex.Index,
        _embedding_dim: int,
        _embedding_dtype: type[Any] = np.float16,
        _ui_loaded: bool = False,
        _ui_updated: bool = False,
    ):
        super().__init__(
            db_path=epath.Path(db_path),
            db=db,
            ui=ui,
            _embedding_dim=_embedding_dim,
            _embedding_dtype=_embedding_dtype,
            _ui_loaded=_ui_loaded,
            _ui_updated=_ui_updated,
        )

    @classmethod
    def create(
        cls,
        db_path: str,
        usearch_cfg: config_dict.ConfigDict | None = None,
    ) -> "SQLiteUsearchDBExt":
        """
        Create a new SQLiteUsearchDBExt instance.
        """
        sqlite_usearch = super().create(db_path, usearch_cfg)
        return cls(
            db_path=db_path,
            db=sqlite_usearch.db,
            ui=sqlite_usearch.ui,
            _embedding_dim=sqlite_usearch._embedding_dim,
            _embedding_dtype=sqlite_usearch._embedding_dtype,
        )

    def count_recordings(self) -> int:
        """
        Get the number of sources in the db.
        """
        cursor = self._get_cursor()
        cursor.execute("SELECT COUNT(*) FROM recordings")
        return cursor.fetchone()[0]
