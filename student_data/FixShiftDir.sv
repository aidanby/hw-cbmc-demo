// 8-bit shift register: shifts right on each clock edge, din enters at MSB.
// The shift register is not producing the correct output sequence.
module shift_reg(input clk, input reset, input din, output reg [7:0] q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 8'hFF;
    else
      q <= {q[5:0], din, q[7]};
  end

  p_reset: assert property (@(posedge clk) reset |=> q == 8'd0);
  p_msb:   assert property (@(posedge clk) !reset |=> q[7] == $past(din));
  p_lsb1:  assert property (@(posedge clk) !reset |=> q[6] == $past(q[7]));
  p_chain: assert property (@(posedge clk) !reset |=> q[5:0] == $past(q[6:1]));
endmodule
