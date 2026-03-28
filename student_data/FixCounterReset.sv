// 8-bit counter with synchronous reset.
// The counter is not behaving correctly when reset is asserted or counting.
module counter(input clk, input reset, output reg [7:0] count);
  initial count = 0;
  always @(posedge clk) begin
    if (!reset)
      count <= 0;
    else
      count <= count + 2;
  end

  p_reset:       assert property (@(posedge clk) reset |=> count == 0);
  p_inc:         assert property (@(posedge clk) !reset && count < 255 |=> count == $past(count) + 1);
  p_single_step: assert property (@(posedge clk) !reset && count < 255 |=> count <= $past(count) + 1);
endmodule
