// D flip-flop with synchronous enable.
// The flip-flop is not behaving correctly on reset or when enable is deasserted.
module dff_enable(input clk, input reset, input enable, input d, output reg q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 1;
    else
      q <= d;
  end

  p_reset:     assert property (@(posedge clk) reset |=> q == 0);
  p_hold:      assert property (@(posedge clk) !reset && !enable |=> q == $past(q));
  p_capture:   assert property (@(posedge clk) !reset && enable |=> q == $past(d));
  p_reset_clr: assert property (@(posedge clk) reset && $past(reset) |=> q == 0);
endmodule
