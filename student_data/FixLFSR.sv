// 4-bit maximal-length LFSR. Correct feedback: q[3] ^ q[2].
// The LFSR has bugs in initial seed, reset value, and feedback polynomial.
module lfsr4(input clk, input reset, output reg [3:0] q);
  initial q = 4'h0;  // Bug 1: should be 4'h1 (zero seed locks up without reset)

  always @(posedge clk) begin
    if (reset)
      q <= 4'h4;              // Bug 2: should be 4'h1
    else
      q <= {q[2:0], q[3]^q[1]};  // Bug 3: wrong taps, should be q[3]^q[2]
  end

  p_nonzero:    assert property (@(posedge clk) !reset |=> q != 4'h0);
  p_reset_seed: assert property (@(posedge clk) reset |=> q == 4'h1);
  p_step_4:     assert property (@(posedge clk) !reset && q == 4'h4 |=> q == 4'h9);
endmodule
