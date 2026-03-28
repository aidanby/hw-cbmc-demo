// D flip-flop with synchronous enable.
// The flip-flop is not holding its value correctly when enable is deasserted.
module dff_enable(input clk, input reset, input enable, input d, output reg q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 0;
    else
      q <= d;
  end

  p_hold:    assert property (@(posedge clk) !reset && !enable |=> q == $past(q));
  p_capture: assert property (@(posedge clk) !reset && enable |=> q == $past(d));
endmodule
