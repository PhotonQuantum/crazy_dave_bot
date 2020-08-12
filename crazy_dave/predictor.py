import asyncio
from dataclasses import asdict, dataclass
from enum import IntEnum, auto
from typing import List, Optional, Tuple, Union
from urllib.parse import urljoin

from aiohttp import ClientSession


class PredictMode(IntEnum):
    Legacy = auto()
    S2S = auto()


@dataclass
class LSTMParams:
    sentence: str
    temp: int = 1
    n: int = 1


@dataclass
class S2SParams:
    sentence: str
    temp: int = 1
    b: int = 20
    b_topk: int = 5
    mode: str = "beam"


@dataclass(frozen=True)
class UpdateResult:
    updated: bool
    current_version: str
    from_version: Optional[str] = None


@dataclass(frozen=True)
class PredictResult:
    text: str
    response: dict
    request: dict
    mode: PredictMode

    def dumps(self) -> dict:
        rtn = asdict(self)
        rtn["mode"] = self.mode.name
        return rtn


class Predictor:
    def __init__(self, s2s_url, lstm_url):
        self._s2s_url = s2s_url
        self._lstm_url = lstm_url
        self._update_lock = asyncio.Lock()
        self._session = ClientSession()

    async def predict(self, sentences: Union[str, List[str]], force_legacy: bool = False) -> PredictResult:
        legacy = force_legacy or isinstance(sentences, list)
        url = self._lstm_url if legacy else self._s2s_url

        if isinstance(sentences, list):
            _sentences = sentences
        elif isinstance(sentences, str):
            _sentences = [sentences]
        else:
            raise KeyError
        payload = {"sentences": _sentences}

        async with self._session.post(urljoin(url, "infer"), json=payload) as r:
            raw = await r.json()

        response = raw["response"]
        text = " ".join(response)
        return PredictResult(text, raw, payload, PredictMode.Legacy if legacy else PredictMode.S2S)

    async def update_model(self) -> Tuple[UpdateResult, UpdateResult]:
        async def fetch(url):
            async with self._session.post(url) as r:
                return await r.json()

        def parse_result(result):
            if result["updated"]:
                return UpdateResult(True, result["current_version"], result["from_version"])
            return UpdateResult(False, result["current_version"])

        async with self._update_lock:
            update_lstm = fetch(urljoin(self._lstm_url, "update"))
            update_s2s = fetch(urljoin(self._s2s_url, "update"))
            results = await asyncio.gather(update_lstm, update_s2s)
            # noinspection PyTypeChecker
            return [parse_result(result) for result in results]

    async def close(self):
        await self._session.close()
