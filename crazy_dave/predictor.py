import asyncio
from dataclasses import asdict, dataclass
from typing import List, Optional, Tuple, Union
from urllib.parse import urljoin

from aiohttp import ClientSession


@dataclass
class LSTMParams:
    sentence: str
    temp: int = 1
    b: int = 20
    b_topk: int = 5
    mode: str = "beam"


@dataclass
class S2SParams:
    sentence: str
    temp: int = 1
    n: int = 1


@dataclass(frozen=True)
class UpdateResult:
    updated: bool
    current_version: str
    old_version: Optional[str] = None


class Predictor:
    def __init__(self, s2s_url, lstm_url):
        self._s2s_url = s2s_url
        self._lstm_url = lstm_url
        self._update_lock = asyncio.Lock()
        self._session = ClientSession()

    async def predict(self, sentences: Union[str, List[str]], force_legacy: bool = False) -> Tuple[str, dict]:
        legacy = force_legacy or isinstance(sentences, list)

        if legacy:
            input_sentences = ";".join(x.strip() for x in sentences)
            async with self._session.get(urljoin(self._lstm_url, "infer"),
                                         params=asdict(LSTMParams(input_sentences))) as r:
                raw = await r.json()
        else:
            async with self._session.get(urljoin(self._s2s_url, "infer"), params=asdict(S2SParams(sentences))) as r:
                raw = await r.json()

        raw = await r.json()
        response = raw["response"]
        if legacy:
            return " ".join(response.strip(";").split(";")), raw
        return " ".join(response.strip("EOS").split("EOS")), raw

    async def update_model(self) -> Tuple[UpdateResult, UpdateResult]:
        async def fetch(url):
            async with self._session.get(url) as r:
                return await r.json()

        def parse_result(result):
            if result["updated"]:
                return UpdateResult(True, result["version"], result["old"])
            return UpdateResult(False, result["version"])

        async with self._update_lock:
            update_lstm = fetch(urljoin(self._lstm_url, "update"))
            update_s2s = fetch(urljoin(self._s2s_url, "update"))
            results = await asyncio.gather(update_lstm, update_s2s)
            # noinspection PyTypeChecker
            return [parse_result(result) for result in results]

    async def close(self):
        await self._session.close()
