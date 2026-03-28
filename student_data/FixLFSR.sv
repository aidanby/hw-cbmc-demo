// 4-bit Linear Feedback Shift Register.
// The LFSR is not cycling through all 15 non-zero states correctly.
module lfsr4(input clk, input reset, output reg [3:0] q);
  initial q = 4'h0;

  always @(posedge clk) begin
    if (reset)
      q <= 4'h4;            
    else
      q <= {q[2:0], q[3]^q[1]};
  end

  p_nonzero:    assert property (@(posedge clk) !reset |=> q != 4'h0);
  p_reset_seed: assert property (@(posedge clk) reset |=> q == 4'h1);
  p_step_4:     assert property (@(posedge clk) !reset && q == 4'h4 |=> q == 4'h9);
endmodule
