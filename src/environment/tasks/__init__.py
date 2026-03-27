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
]
