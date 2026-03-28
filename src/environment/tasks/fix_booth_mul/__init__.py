"""fix-booth-mul: Booth radix-2 multiplier has 3 bugs: add and subtract operat..."""
from typing import final

from environment.tasks._base import DebugCircuitTask


@final
class FixBoothMulTask(DebugCircuitTask):
    id = "fix-booth-mul"
    sv_filename = "FixBoothMul.sv"
    config_filename = "fix-booth-mul.json"
    bound = 12
    tier = "4"
    tier_label = "Algorithm / Multi-cycle"
    num_properties = 6
    bug_description = (
        "Booth radix-2 multiplier has 3 bugs: add and subtract operations are"
        " swapped in the Booth encoding (01 should add, 10 should subtract), the"
        " right shift fills with 0 instead of sign-extending A[7], and the"
        " product assembles {A,A} instead of {A,Q}"
    )
    hint = (
        "Booth encoding table: {Q[0],Q_neg1}=01 means ADD M, =10 means SUBTRACT"
        " M. The shift must be ARITHMETIC (sign-extend A[7]). The final product"
        " is the concatenation of accumulator A (upper) and shifted multiplier Q"
        " (lower)."
    )
