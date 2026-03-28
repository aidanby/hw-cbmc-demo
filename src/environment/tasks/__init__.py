"""hw-cbmc formal verification task registry.

Import all task classes so the environment can discover them.
"""

from environment.tasks.fix_adder_carry import FixAdderCarryTask
from environment.tasks.fix_mux_select import FixMuxSelectTask
from environment.tasks.fix_decoder import FixDecoderTask
from environment.tasks.fix_counter_reset import FixCounterResetTask
from environment.tasks.fix_counter_wrap import FixCounterWrapTask
from environment.tasks.fix_shift_dir import FixShiftDirTask
from environment.tasks.fix_dff_enable import FixDffEnableTask
from environment.tasks.fix_traffic_light import FixTrafficLightTask
from environment.tasks.fix_arbiter_fair import FixArbiterFairTask
from environment.tasks.fix_ring_buffer import FixRingBufferTask
from environment.tasks.fix_smv_counter import FixSmvCounterTask
from environment.tasks.fix_smv_onehot import FixSmvOnehotTask
from environment.tasks.fix_priority_enc import FixPriorityEncTask
from environment.tasks.fix_fibonacci import FixFibonacciTask
from environment.tasks.fix_lfsr import FixLFSRTask
from environment.tasks.fix_gray_counter import FixGrayCounterTask
from environment.tasks.fix_crc8 import FixCRC8Task
from environment.tasks.fix_hamming import FixHammingTask
from environment.tasks.fix_barrel_shift import FixBarrelShiftTask
from environment.tasks.fix_smv_ring3 import FixSmvRing3Task
from environment.tasks.fix_smv_mod8 import FixSmvMod8Task

__all__ = [
    "FixAdderCarryTask",
    "FixMuxSelectTask",
    "FixDecoderTask",
    "FixCounterResetTask",
    "FixCounterWrapTask",
    "FixShiftDirTask",
    "FixDffEnableTask",
    "FixTrafficLightTask",
    "FixArbiterFairTask",
    "FixRingBufferTask",
    "FixSmvCounterTask",
    "FixSmvOnehotTask",
    "FixPriorityEncTask",
    "FixFibonacciTask",
    "FixLFSRTask",
    "FixGrayCounterTask",
    "FixCRC8Task",
    "FixHammingTask",
    "FixBarrelShiftTask",
    "FixSmvRing3Task",
    "FixSmvMod8Task",
]
