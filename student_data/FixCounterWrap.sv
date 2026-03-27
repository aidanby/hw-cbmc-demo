// BCD counter: counts 0-9 and wraps back to 0.
// BUG: counter wraps at 15 (4'hF) instead of 9 (4'd9).
// Fix the wrap condition so all properties pass.
module bcd_counter(input clk, input reset, output reg [3:0] count);
  initial count = 0;
  always @(posedge clk) begin
    if (reset)
      count <= 0;
    else if (count == 4'd15)  // BUG: should be 4'd9
      count <= 0;
    else
      count <= count + 1;
  end

  p_range:  assert property (@(posedge clk) count <= 9);
  p_wrap:   assert property (@(posedge clk) count == 9 |=> count == 0);
  p_inc:    assert property (@(posedge clk) !reset && count < 9 |=> count == $past(count) + 1);
endmodule
