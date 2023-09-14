from dataclasses import dataclass
from typing import List, Optional

from ..nomoduleroot.modulechild.leaf import OakLeaf
from ..nomoduleroot.modulechild.leaf import CommownLeaf as CommonLeaf


@dataclass
class Branch:
    length: float

@dataclass
class OakBranch(Branch):
    sub_branches: List['OakBranch']
    leaves: List[OakLeaf]

@dataclass
class BirchLeaf(CommonLeaf):
    color: Optional[str]
