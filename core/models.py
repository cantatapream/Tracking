"""
SPT 데이터 모델 - 대원, 장비, 선박 정의
"""
from dataclasses import dataclass, field, asdict
from typing import Optional
import time


@dataclass
class Personnel:
    """대원 데이터 모델"""
    id: str
    name: str
    rank: str  # 계급: 경정, 경감, 경위, 순경 등
    department: str = ""  # 소속
    location: str = "base"  # 현재 위치: base, patrol_RIB-1, vessel_VESSEL-A 등
    status: str = "standby"  # standby, active, on-air
    deploy_timestamp: Optional[float] = None  # 투입 시각 (unix timestamp)
    last_return_timestamp: Optional[float] = None  # 마지막 본함 복귀 시각
    total_deploy_seconds: float = 0.0  # 누적 탑승 시간 (초)
    meal_timestamp: Optional[float] = None  # 마지막 식사 시각
    has_been_deployed: bool = False  # 한 번이라도 출동한 적 있는지

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Personnel":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def deploy_to(self, location: str, timestamp: float = None):
        """대원을 특정 위치로 이동"""
        ts = timestamp or time.time()
        old_location = self.location

        # 본함이 아닌 곳에서 복귀하는 경우 누적 시간 계산
        if self.location != "base" and self.deploy_timestamp:
            elapsed = ts - self.deploy_timestamp
            self.total_deploy_seconds += elapsed

        if location == "base":
            # 본함 복귀
            self.last_return_timestamp = ts
            self.deploy_timestamp = None
            self.status = "standby"
        else:
            # 단정 또는 어선으로 이동
            self.deploy_timestamp = ts
            self.status = "active"
            self.has_been_deployed = True

        self.location = location
        return old_location

    def get_deploy_elapsed(self) -> float:
        """현재 투입 경과 시간 (초)"""
        if self.deploy_timestamp and self.location != "base":
            return time.time() - self.deploy_timestamp
        return 0.0

    def get_rest_elapsed(self) -> float:
        """본함 복귀 후 휴식 경과 시간 (초)"""
        if self.location == "base" and self.last_return_timestamp and self.has_been_deployed:
            return time.time() - self.last_return_timestamp
        return 0.0


@dataclass
class Equipment:
    """장비 데이터 모델"""
    id: str
    name: str
    category: str = ""  # 엔진, 통신기기, GPS 등
    vessel_id: str = ""  # 소속 선박
    assignee_id: Optional[str] = None  # 담당자 ID
    is_running: bool = False  # 가동 중 여부
    run_start_timestamp: Optional[float] = None  # 가동 시작 시각
    total_run_seconds: float = 0.0  # 누적 가동 시간

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Equipment":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def start(self):
        if not self.is_running:
            self.is_running = True
            self.run_start_timestamp = time.time()

    def stop(self):
        if self.is_running and self.run_start_timestamp:
            self.total_run_seconds += time.time() - self.run_start_timestamp
            self.is_running = False
            self.run_start_timestamp = None

    def reset_timer(self):
        self.stop()
        self.total_run_seconds = 0.0

    def get_run_elapsed(self) -> float:
        total = self.total_run_seconds
        if self.is_running and self.run_start_timestamp:
            total += time.time() - self.run_start_timestamp
        return total


# 기본 선박 구조 정의
DEFAULT_VESSELS = {
    "base": {"name": "본함 (KCG 3012)", "type": "base"},
    "patrol_RIB-1": {"name": "단정 1 (RIB-1)", "type": "patrol"},
    "patrol_RIB-2": {"name": "단정 2 (RIB-2)", "type": "patrol"},
    "patrol_RIB-3": {"name": "단정 3 (RIB-3)", "type": "patrol"},
    "patrol_RIB-4": {"name": "단정 4 (RIB-4)", "type": "patrol"},
    "vessel_VESSEL-A": {"name": "중국어선 A (CH-VESSEL A)", "type": "vessel"},
    "vessel_VESSEL-B": {"name": "중국어선 B (CH-VESSEL B)", "type": "vessel"},
}

DEFAULT_PERSONNEL = [
    Personnel(id="P001", name="김진우", rank="경정", department="본함"),
    Personnel(id="P002", name="이영호", rank="경감", department="본함"),
    Personnel(id="P003", name="최유진", rank="경위", department="본함"),
    Personnel(id="P004", name="박도윤", rank="경장", department="본함"),
    Personnel(id="P005", name="강민재", rank="상사", department="본함"),
    Personnel(id="P006", name="이대우", rank="경장", department="본함"),
    Personnel(id="P007", name="박근서", rank="순경", department="본함"),
    Personnel(id="P008", name="최완수", rank="순경", department="본함"),
    Personnel(id="P009", name="강현우", rank="경장", department="본함"),
    Personnel(id="P010", name="서시봉", rank="순경", department="본함"),
    Personnel(id="P011", name="김연석", rank="순경", department="본함"),
    Personnel(id="P012", name="강차욱", rank="경장", department="본함"),
    Personnel(id="P013", name="강동원", rank="하사", department="본함"),
    Personnel(id="P014", name="정해인", rank="경위", department="본함"),
    Personnel(id="P015", name="박서준", rank="상사", department="본함"),
]
