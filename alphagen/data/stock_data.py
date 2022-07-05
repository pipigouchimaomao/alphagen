from typing import List, Dict, Optional, Union
import numpy as np
import pandas as pd
import torch


class StockData:
    _qlib_initialized: bool = False

    def __init__(self,
                 instrument: str,
                 start_time: str,
                 end_time: str,
                 max_backtrack_days: int,
                 features: List[str],
                 device: torch.device = torch.device("cpu")) -> None:
        self._init_qlib()

        self._instrument = instrument
        self._start_time = start_time
        self._end_time = end_time
        self.max_backtrack_days = max_backtrack_days
        self._features = features
        self._device = device
        self.data = self._get_data()

    @classmethod
    def _init_qlib(cls) -> None:
        if cls._qlib_initialized:
            return
        import qlib
        from qlib.config import REG_CN
        qlib.init(provider_uri="~/.qlib/qlib_data/cn_data", region=REG_CN)
        cls._qlib_initialized = True

    def _load_exprs(self, exprs: Union[str, List[str]]) -> pd.DataFrame:
        # This evaluates an expression on the data and returns the dataframe
        # It might throw on illegal expressions like "Ref(constant, dtime)"
        from qlib.data.dataset.loader import QlibDataLoader
        from qlib.data import D
        if not isinstance(exprs, list):
            exprs = [exprs]
        cal: np.ndarray = D.calendar()
        start_index = cal.searchsorted(pd.Timestamp(self._start_time))  # type: ignore
        real_start_time = cal[start_index - self.max_backtrack_days]
        return (QlibDataLoader(config=exprs)    # type: ignore
                .load(self._instrument, real_start_time, self._end_time))

    def _get_data(self) -> torch.Tensor:
        # FIXME: hardcoded...
        features = ["$open", "$close", "$high", "$low", "$volume"]
        df = self._load_exprs(features)
        df = df.stack().unstack(level=1)
        values = df.values
        values = values.reshape((-1, len(features), values.shape[-1]))  # type: ignore
        return torch.tensor(values, dtype=torch.float, device=self._device)

    @property
    def n_features(self) -> int: return 5   # FIXME: hardcoded

    @property
    def n_stocks(self) -> int: return self.data.shape[-1]

    @property
    def n_days(self) -> int: return self.data.shape[0] - self.max_backtrack_days
