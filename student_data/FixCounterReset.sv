// 8-bit counter with synchronous reset.
// BUG: reset polarity is inverted — fix it so all properties pass.
module counter(input clk, input reset, output reg [7:0] count);
  initial count = 0;
  always @(posedge clk) begin
    if (!reset)    // BUG: should be (reset), not (!reset)
      count <= 0;
    else
      count <= count + 1;
  end

  p_reset: assert property (@(posedge clk) reset |=> count == 0);
  p_inc:   assert property (@(posedge clk) !reset && count < 255 |=> count == $past(count) + 1);
endmodule
