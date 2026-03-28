// 8-bit shift register: shifts right on each clock edge.
// The shift register is not producing the correct output sequence.
module shift_reg(input clk, input reset, input din, output reg [7:0] q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 8'b0;
    else
      q <= {q[6:0], din};
  end

  p_msb:  assert property (@(posedge clk) !reset |=> q[7] == $past(din));
  p_lsb1: assert property (@(posedge clk) !reset |=> q[6] == $past(q[7]));
endmodule
