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
from environment.tasks.fix_pipeline_alu import FixPipelineAluTask
from environment.tasks.implement_arb3 import ImplementArb3Task
from environment.tasks.fix_watchdog import FixWatchdogTask
from environment.tasks.fix_spi_slave import FixSpiSlaveTask
from environment.tasks.fix_restoring_div import FixRestoringDivTask
from environment.tasks.implement_axi_handshake import ImplementAxiHandshakeTask
from environment.tasks.fix_fifo_ptrs import FixFifoPtrsTask
from environment.tasks.fix_fifo_credit import FixFifoCreditTask
from environment.tasks.fix_pipeline_mac import FixPipelineMacTask
from environment.tasks.fix_uart_rx import FixUartRxTask
from environment.tasks.fix_i2c_ctrl import FixI2cCtrlTask
from environment.tasks.fix_booth_mul import FixBoothMulTask
from environment.tasks.fix_scoreboard_bypass import FixScoreboardBypassTask
from environment.tasks.fix_cache_ctrl import FixCacheCtrlTask
from environment.tasks.fix_branch_pred import FixBranchPredTask
from environment.tasks.fix_dma_engine import FixDmaEngineTask
from environment.tasks.fix_regfile_fwd import FixRegfileFwdTask
from environment.tasks.fix_hazard_ctrl import FixHazardCtrlTask
from environment.tasks.fix_arb_lock import FixArbLockTask
from environment.tasks.fix_fifo_async import FixFifoAsyncTask
from environment.tasks.fix_timer_irq import FixTimerIrqTask
from environment.tasks.fix_mem_ctrl import FixMemCtrlTask

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
    "FixPipelineAluTask",
    "ImplementArb3Task",
    "FixWatchdogTask",
    "FixSpiSlaveTask",
    "FixRestoringDivTask",
    "ImplementAxiHandshakeTask",
    "FixFifoPtrsTask",
    "FixFifoCreditTask",
    "FixPipelineMacTask",
    "FixUartRxTask",
    "FixI2cCtrlTask",
    "FixBoothMulTask",
    "FixScoreboardBypassTask",
    "FixCacheCtrlTask",
    "FixBranchPredTask",
    "FixDmaEngineTask",
    "FixRegfileFwdTask",
    "FixHazardCtrlTask",
    "FixArbLockTask",
    "FixFifoAsyncTask",
    "FixTimerIrqTask",
    "FixMemCtrlTask",
]
