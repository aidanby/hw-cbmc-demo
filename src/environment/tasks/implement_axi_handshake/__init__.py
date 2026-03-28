"""implement-axi-handshake: implement AXI-lite write channel handshake FSM."""
from typing import final

from environment.tasks._base import ImplementModuleTask


@final
class ImplementAxiHandshakeTask(ImplementModuleTask):
    id = "implement-axi-handshake"
    sv_filename = "ImplementAxiHandshake.sv"
    config_filename = "implement-axi-handshake.json"
    bound = 10
    tier = "4"
    tier_label = "Protocol FSM"
    num_properties = 6
