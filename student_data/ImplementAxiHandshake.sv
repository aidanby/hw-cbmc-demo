// AXI-lite write channel handshake controller.
//
// The master drives AWVALID and WVALID. The slave drives AWREADY, WREADY,
// and BRESP_VALID.  A channel transfer completes when VALID & READY are
// high on the same clock edge.
//
// Environment constraints (given as `assume`):
//   - Once AWVALID goes high it stays high until AWREADY fires.
//   - Once WVALID goes high it stays high until WREADY fires.
//
// Required behavior (assert properties you must satisfy):
//   1. READY only when the corresponding VALID is present.
//   2. BRESP is a one-cycle pulse and does not fire right after reset.
//   3. When both VALID signals are held, BRESP fires within a few cycles.
//   4. When both channels are stalled (VALID high, READY low), progress
//      is made on the next cycle.
//
// Your task: fill the always block so ALL assertions PROVE with:
//     ebmc /workdir/data/ImplementAxiHandshake.sv --bound 10
//
// Hints
//   - A 4-state FSM (IDLE / AW_DONE / W_DONE / RESPOND) works well.
//   - In IDLE, accept whichever channels have VALID (both, AW only, W only).
//   - In AW_DONE/W_DONE, wait for the other channel.
//   - In RESPOND, pulse bresp_valid and return to IDLE.
//   - You will need an `initial` block to set register starting values —
//     EBMC checks properties from time 0.
module axi_write_ctrl(
  input  clk,
  input  reset,
  input  awvalid,
  input  wvalid,
  output reg awready,
  output reg wready,
  output reg bresp_valid
);
  // TODO: declare any internal state you need (e.g. FSM state register)

  // TODO: add an initial block to set starting values for all registers

  always @(posedge clk) begin
    if (reset) begin
      awready     <= 1'b0;
      wready      <= 1'b0;
      bresp_valid <= 1'b0;
    end else begin
      // TODO: implement FSM transitions
      awready     <= 1'b0;
      wready      <= 1'b0;
      bresp_valid <= 1'b0;
    end
  end

  // ── Environment constraints (AXI-lite protocol) ──
  aw_hold: assume property (@(posedge clk) awvalid && !awready |=> awvalid);
  w_hold:  assume property (@(posedge clk) wvalid  && !wready  |=> wvalid);

  // ── Properties the implementation must satisfy ──
  // Safety: READY only when VALID present
  p_aw_valid:   assert property (@(posedge clk) awready |-> awvalid);
  p_w_valid:    assert property (@(posedge clk) wready  |-> wvalid);
  // Reset clears response
  p_reset:      assert property (@(posedge clk) reset |=> !bresp_valid);
  // BRESP is a one-cycle pulse
  p_bresp_pulse: assert property (@(posedge clk) bresp_valid |=> !bresp_valid);
  // Both channels stalled ⇒ at least one accepted next cycle
  p_no_stall:   assert property (@(posedge clk) !reset && awvalid && !awready && wvalid && !wready |=> awready || wready);
  // Both VALIDs held two cycles ⇒ BRESP within two more cycles (reset excuses)
  p_both_resp:  assert property (@(posedge clk) !reset && awvalid && wvalid && $past(awvalid && wvalid) |=> ##[0:2] (bresp_valid || reset));
endmodule
