// D flip-flop with synchronous enable.
// BUG: output updates on every clock edge, ignoring the enable signal.
// Fix the enable logic so all properties pass.
module dff_enable(input clk, input reset, input enable, input d, output reg q);
  initial q = 0;
  always @(posedge clk) begin
    if (reset)
      q <= 0;
    else
      q <= d;  // BUG: ignores enable — should be: if (enable) q <= d;
  end

  p_hold:   assert property (@(posedge clk) !reset && !enable |=> q == $past(q));
  p_capture: assert property (@(posedge clk) !reset && enable |=> q == $past(d));
endmodule
