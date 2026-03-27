// 8-bit shift register: shifts right on each clock edge.
// BUG: shift register shifts left instead of right.
// Fix the shift direction so all properties pass.
module shift_reg(input clk, input reset, input din, output reg [7:0] q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 8'b0;
    else
      q <= {q[6:0], din};  // BUG: left shift — should be {din, q[7:1]} (right shift)
  end

  p_msb:  assert property (@(posedge clk) !reset |=> q[7] == $past(din));
  p_lsb1: assert property (@(posedge clk) !reset |=> q[6] == $past(q[7]));
endmodule
